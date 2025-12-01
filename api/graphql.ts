import { ApolloServer } from 'apollo-server-micro';
import { typeDefs } from '../gateway/src/schema';
import { resolvers } from '../gateway/src/resolvers';
import { initDb } from '../gateway/src/db';

// Initialize DB connection
// Note: In a serverless environment, managing DB connections can be tricky.
// Ideally, use a connection pool or a serverless-friendly DB driver.
let dbInitialized = false;

const server = new ApolloServer({
  typeDefs,
  resolvers,
  introspection: true,
  context: ({ req }) => ({
    // Pass headers or auth tokens here
    headers: req.headers
  })
});

const startServer = server.start();

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');

  if (req.method === 'OPTIONS') {
    res.end();
    return;
  }

  if (!dbInitialized) {
    try {
        await initDb();
        dbInitialized = true;
    } catch (e) {
        console.error("DB Init failed", e);
        // Continue, as some resolvers might not need DB or will fail gracefully
    }
  }

  await startServer;
  await server.createHandler({ path: '/graphql' })(req, res);
}
