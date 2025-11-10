import "dotenv/config";
import express from "express";
import { ApolloServer } from "apollo-server-express";
const { graphqlUploadExpress } = require("graphql-upload");
import { typeDefs } from "./schema";
import { resolvers } from "./resolvers";
import { initDb } from "./db";
import { ensureStorageDirs } from "./services/storage";

const PORT = process.env.PORT || 4000;

async function start() {
    await initDb();
    ensureStorageDirs();

    const app = express();

    // Middleware for file uploads (GraphQL multipart)
    app.use(graphqlUploadExpress({ maxFileSize: 10_000_000, maxFiles: 1 }));

    const server = new ApolloServer({
        typeDefs,
        resolvers,
    });

    await server.start();
    server.applyMiddleware({ app, path: "/graphql" });

    app.get("/health", (_req, res) => {
        res.json({ status: "ok" });
    });

    app.listen(PORT, () => {
        console.log(`Gateway listening on http://localhost:${PORT}/graphql`);
    });
}

start().catch((err) => {
    console.error("Failed to start gateway:", err);
    process.exit(1);
});
