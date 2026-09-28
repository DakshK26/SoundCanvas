// public graphql API (sits behind the ALB). creates jobs, queues them, reports status.
// the actual work happens in worker.ts - same docker image, different command
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

const PORT = 4000;
const FRONTEND_ORIGIN = requireEnv("FRONTEND_ORIGIN"); // CORS - only the frontend can call this from a browser
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// X-Client-Id isn't auth, it's just a random uuid the browser keeps so I can group its
// requests (history, rate limit). validating it as a uuid so junk doesn't end up in the db
function requestContext(req: Request): Context {
  const clientId = req.header("X-Client-Id");
  if (!clientId || !UUID_PATTERN.test(clientId)) {
    throw new GraphQLError("Missing or invalid X-Client-Id header", {
      extensions: { code: "BAD_REQUEST", http: { status: 400 } },
    });
  }
  return { clientId, clientIp: req.ip! };
}

// apollo doesn't log resolver errors by default, it just returns them. so a db/S3 blowup
// would show up in the 5xx alarm with nothing in the logs. this logs anything that ISN'T one
// of my own GraphQLErrors (RATE_LIMITED etc are expected, no need to log those)
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
  // NODE_ENV=production (Dockerfile) -> apollo disables introspection + strips stack traces
  const server = new ApolloServer<Context>({ typeDefs, resolvers, plugins: [logUnexpectedErrors] });
  await server.start();

  const app = express();
  // gotcha: without this req.ip is the ALB's ip, so the rate limit lumped everyone together.
  // 1 = trust exactly one hop (the ALB), so people can't spoof X-Forwarded-For past it
  app.set("trust proxy", 1);
  app.get("/health", (_, res) => { res.send("ok"); }); // ALB target group health check
  app.use(
    "/graphql",
    cors({ origin: FRONTEND_ORIGIN }),
    express.json({ limit: "10kb" }), // queries are a few hundred bytes, files never come thru here
    expressMiddleware(server, { context: async ({ req }) => requestContext(req) }),
  );
  const httpServer = app.listen(PORT, () => log.info("GraphQL API ready", { port: PORT }));

  // deploys/scale-in: ECS pulls the task out of the ALB, then SIGTERMs it.
  // let in-flight requests finish, then close the pool
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
