// The public GraphQL API, behind the load balancer. It creates jobs, queues
// them on SQS and reports their status; the worker (worker.ts) runs them.
import { ApolloServer } from "@apollo/server";
import { expressMiddleware } from "@apollo/server/express4";
import cors from "cors";
import express, { Request } from "express";
import { GraphQLError } from "graphql";
import { createTable } from "./db";
import { requireEnv } from "./env";
import { Context, resolvers } from "./resolvers";
import { typeDefs } from "./schema";

const PORT = 4000;
const FRONTEND_ORIGIN = requireEnv("FRONTEND_ORIGIN"); // browsers may only call the API from this site
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Reads who is calling. The client id is anonymous, not a login: it only groups one browser's requests. */
function requestContext(req: Request): Context {
  const clientId = req.header("X-Client-Id");
  if (!clientId || !UUID_PATTERN.test(clientId)) {
    throw new GraphQLError("Missing or invalid X-Client-Id header", {
      extensions: { code: "BAD_REQUEST", http: { status: 400 } },
    });
  }
  return { clientId, clientIp: req.ip! };
}

async function main(): Promise<void> {
  await createTable();
  const server = new ApolloServer<Context>({ typeDefs, resolvers });
  await server.start();

  const app = express();
  app.set("trust proxy", 1); // trust one hop, the load balancer, so req.ip is the browser's address
  app.get("/health", (_, res) => { res.send("ok"); }); // load balancer health check
  app.use(
    "/graphql",
    cors({ origin: FRONTEND_ORIGIN }),
    express.json(),
    expressMiddleware(server, { context: async ({ req }) => requestContext(req) }),
  );
  app.listen(PORT, () => console.log(`GraphQL API ready on port ${PORT}`));
}

main();
