import "dotenv/config";
import express from "express";
import cors from "cors";
import { createProxyMiddleware, Options } from "http-proxy-middleware";
import { ApolloServer } from "apollo-server-express";
import { graphqlUploadExpress } from "graphql-upload-minimal";
import { typeDefs } from "./schema";
import { resolvers } from "./resolvers";
import { initDb } from "./db";
import { IncomingMessage, ServerResponse } from "http";

const PORT = process.env.PORT || 4000;
const HOST = process.env.HOST || "0.0.0.0";
const S3_ENDPOINT = process.env.S3_ENDPOINT || "http://localhost:9002";

async function start() {
  await initDb();

  const app = express();

  // Enable CORS for all origins (Vercel frontend)
  app.use(cors({
    origin: true,
    credentials: true,
  }));

  // Proxy /s3/* requests to MinIO (for presigned URLs)
  const proxyOptions: Options = {
    target: S3_ENDPOINT,
    changeOrigin: true,
    pathRewrite: { '^/s3': '' },
    on: {
      proxyRes: (proxyRes: IncomingMessage) => {
        // Add CORS headers to MinIO responses
        (proxyRes as any).headers = (proxyRes as any).headers || {};
        (proxyRes as any).headers['access-control-allow-origin'] = '*';
        (proxyRes as any).headers['access-control-allow-methods'] = 'GET, PUT, POST, DELETE, OPTIONS';
        (proxyRes as any).headers['access-control-allow-headers'] = '*';
        (proxyRes as any).headers['access-control-expose-headers'] = '*';
      },
    },
  };
  app.use('/s3', createProxyMiddleware(proxyOptions));

  // Middleware for file uploads (GraphQL multipart)
  app.use(graphqlUploadExpress({ maxFileSize: 10_000_000, maxFiles: 1 }) as any);

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

  app.listen(Number(PORT), HOST, () => {
    console.log(`Gateway listening on http://${HOST}:${PORT}/graphql`);
  });
}

start().catch((err) => {
  console.error("Failed to start gateway:", err);
  process.exit(1);
});