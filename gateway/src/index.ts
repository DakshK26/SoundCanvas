import "dotenv/config";
import express from "express";
import cors from "cors";
import { ApolloServer } from "apollo-server-express";
import { graphqlUploadExpress } from "graphql-upload-minimal";
import { typeDefs } from "./schema";
import { resolvers } from "./resolvers";
import { initDb } from "./db";
import { S3Client, PutObjectCommand, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

const PORT = process.env.PORT || 4000;
const HOST = process.env.HOST || "0.0.0.0";
const S3_ENDPOINT = process.env.S3_ENDPOINT || "http://localhost:9002";
const S3_BUCKET_NAME = process.env.S3_BUCKET_NAME || "soundcanvas-uploads";
const AWS_REGION = process.env.AWS_REGION || "us-east-1";

// Internal S3 client for direct operations
const s3Client = new S3Client({
  region: AWS_REGION,
  endpoint: S3_ENDPOINT,
  forcePathStyle: true,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID || "minioadmin",
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || "minioadmin",
  },
});

async function start() {
  await initDb();

  const app = express();

  // Set timeout for long-running operations (5 minutes)
  app.use((req, res, next) => {
    req.setTimeout(5 * 60 * 1000); // 5 minutes
    res.setTimeout(5 * 60 * 1000); // 5 minutes
    next();
  });

  // Enable CORS for all origins (Vercel frontend)
  app.use(cors({
    origin: true,
    credentials: true,
  }));

  // Parse raw body for file uploads
  app.use('/upload/:key(*)', express.raw({ type: '*/*', limit: '10mb' }));

  // Direct upload endpoint - bypasses presigned URL issues
  app.put('/upload/:key(*)', async (req, res) => {
    try {
      const key = req.params.key;
      const body = req.body;
      const contentType = req.headers['content-type'] || 'application/octet-stream';

      console.log(`Uploading file: ${key}, size: ${body.length}, type: ${contentType}`);

      const command = new PutObjectCommand({
        Bucket: S3_BUCKET_NAME,
        Key: key,
        Body: body,
        ContentType: contentType,
      });

      await s3Client.send(command);

      res.status(200).json({ success: true, key });
    } catch (error: any) {
      console.error('Upload error:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // Direct download endpoint - serves files from MinIO
  app.get('/files/:key(*)', async (req, res) => {
    try {
      const key = req.params.key;

      const command = new GetObjectCommand({
        Bucket: S3_BUCKET_NAME,
        Key: key,
      });

      const response = await s3Client.send(command);

      if (response.ContentType) {
        res.setHeader('Content-Type', response.ContentType);
      }
      if (response.ContentLength) {
        res.setHeader('Content-Length', response.ContentLength);
      }

      // Stream the response
      const stream = response.Body as any;
      stream.pipe(res);
    } catch (error: any) {
      console.error('Download error:', error);
      if (error.name === 'NoSuchKey') {
        res.status(404).json({ error: 'File not found' });
      } else {
        res.status(500).json({ error: error.message });
      }
    }
  });

  // Middleware for file uploads (GraphQL multipart)
  app.use(graphqlUploadExpress({ maxFileSize: 10_000_000, maxFiles: 1 }) as any);

  const server = new ApolloServer({
    typeDefs,
    resolvers,
    // Increase timeout for long-running music generation operations
    context: ({ req }) => ({ req }),
  });

  await server.start();
  server.applyMiddleware({
    app,
    path: "/graphql",
    // Disable default body parser timeout to allow long operations
    bodyParserConfig: {
      limit: '10mb'
    }
  });

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
  }).timeout = 5 * 60 * 1000; // 5 minutes server timeout
}

start().catch((err) => {
  console.error("Failed to start gateway:", err);
  process.exit(1);
});