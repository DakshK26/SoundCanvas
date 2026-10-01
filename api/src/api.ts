// The GraphQL API process, its own ECS service behind the load balancer. It only talks to MySQL,
// S3 and SQS and answers in milliseconds; the slow song-making happens in worker.ts.
// The browser reaches it through frontend/lib/apolloClient.ts and the ALB in infra/terraform/network.tf.
import { ApolloServer, ApolloServerPlugin } from "@apollo/server";
import { expressMiddleware } from "@apollo/server/express4";
import cors from "cors";
import express, { Request } from "express";
import { GraphQLError } from "graphql";
import { pool } from "./db";
import { requireEnv } from "./env";
import { log } from "./log";
import { Context, resolvers } from "./resolvers";
import { typeDefs } from "./schema";

const PORT = 4000; // must match the api port in ecs.tf and the target group in network.tf
const FRONTEND_ORIGIN = requireEnv("FRONTEND_ORIGIN");
// The shape crypto.randomUUID() produces in frontend/lib/clientId.ts.
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Every resolver gets this context, and requests without a valid X-Client-Id stop here.
// The client id is not auth, just a random id the browser keeps.
function requestContext(req: Request): Context {
  const clientId = req.header("X-Client-Id");
  if (!clientId || !UUID_PATTERN.test(clientId)) {
    throw new GraphQLError("Missing or invalid X-Client-Id header", {
      extensions: { code: "BAD_REQUEST", http: { status: 400 } },
    });
  }
  return { clientId, clientIp: req.ip! };
}

// A GraphQLError is an expected answer like NOT_FOUND or RATE_LIMITED. Anything else is a bug or
// an outage (database, S3), so it gets logged and every 5xx alarm has a log line behind it.
const logUnexpectedErrors: ApolloServerPlugin<Context> = {
  async requestDidStart() {
    return {
      async didEncounterErrors({ errors, operationName }) {
        for (const { originalError } of errors) {
          if (!originalError || originalError instanceof GraphQLError) continue;
          log.error("request failed", { operationName, error: originalError.message });
        }
      },
    };
  },
};

async function main(): Promise<void> {
  // Apollo joins the schema (schema.ts) to the code that answers it (resolvers.ts).
  const server = new ApolloServer<Context>({ typeDefs, resolvers, plugins: [logUnexpectedErrors] });
  await server.start();

  const app = express();
  // Without this req.ip is the ALB's address. 1 trusts only the hop the ALB adds.
  // The rate limit in resolvers.ts counts by this IP.
  app.set("trust proxy", 1);
  // The load balancer's health check (target group in network.tf) calls this.
  app.get("/health", (_, res) => { res.send("ok"); });
  // Every GraphQL request passes three steps in order: CORS for the frontend origin only, a 10 KB
  // JSON body limit (images go straight to S3, never through here), then Apollo with the context.
  app.use(
    "/graphql",
    cors({ origin: FRONTEND_ORIGIN }),
    express.json({ limit: "10kb" }),
    expressMiddleware(server, { context: async ({ req }) => requestContext(req) }),
  );
  const httpServer = app.listen(PORT, () => log.info("GraphQL API ready", { port: PORT }));

  // On a deploy ECS sends SIGTERM: stop accepting connections, finish the open requests, then
  // close Apollo and the database pool.
  process.on("SIGTERM", () => {
    log.info("SIGTERM received: draining requests");
    httpServer.close(async () => {
      await server.stop();
      await pool.end();
    });
  });
}

main().catch((error) => {
  log.error("API failed to start", { error: (error as Error).message });
  process.exit(1);
});
