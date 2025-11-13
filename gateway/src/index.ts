import "dotenv/config";
import express from "express";
import { ApolloServer } from "apollo-server-express";
import { graphqlUploadExpress } from "graphql-upload-minimal";
import { typeDefs } from "./schema";
import { resolvers } from "./resolvers";
import { initDb } from "./db";

const PORT = process.env.PORT || 4000;

async function start() {
  await initDb();

  const app = express();

  // Middleware for file uploads (GraphQL multipart)
  app.use(graphqlUploadExpress({ maxFileSize: 10_000_000, maxFiles: 1 }));

  const server = new ApolloServer({
    typeDefs,
    resolvers,
  });

  await server.start();
  server.applyMiddleware({ app, path: "/graphql" });

  app.get("/health", async (_req, res) => {
    try {
      // Check database connectivity
      const { getGenerationById } = await import("./db");
      await getGenerationById("health-check"); // Will return null but verifies DB connection

      res.json({
        status: "ok",
        timestamp: new Date().toISOString(),
        services: {
          database: "connected",
          graphql: "running"
        }
      });
    } catch (error: any) {
      res.status(503).json({
        status: "error",
        message: "Database connection failed",
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  });

  app.listen(PORT, () => {
    console.log(`Gateway listening on http://localhost:${PORT}/graphql`);
  });
}

start().catch((err) => {
  console.error("Failed to start gateway:", err);
  process.exit(1);
});