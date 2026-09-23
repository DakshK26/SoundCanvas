// The public GraphQL API, behind the load balancer. It creates jobs, queues
// them on SQS and reports their status; the worker (worker.ts) runs them.
import { ApolloServer } from "@apollo/server";
import { startStandaloneServer } from "@apollo/server/standalone";
import { createTable } from "./db";
import { resolvers } from "./resolvers";
import { typeDefs } from "./schema";

const PORT = 4000;

async function main(): Promise<void> {
  await createTable();
  const server = new ApolloServer({ typeDefs, resolvers });
  const { url } = await startStandaloneServer(server, { listen: { port: PORT } });
  console.log(`GraphQL API ready at ${url}`);
}

main();
