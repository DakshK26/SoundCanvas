// What each GraphQL query and mutation does. Everything is scoped to the caller's client id, and
// nothing here is slow: starting a generation only puts a job on the queue for a worker.
// The schema these answer is schema.ts; the browser's side is frontend/graphql/operations.ts.
import { randomUUID } from "crypto";
import { GraphQLError } from "graphql";
import { audioKey, createUploadForm, imageKey, objectExists, signDownloadUrl } from "./aws/s3";
import { enqueueJob } from "./aws/queue";
import {
  countRecentGenerations, deleteGeneration, Generation, getGeneration, insertGeneration, listGenerations,
  markPending, markQueued,
} from "./db";

// Built for every request by requestContext in api.ts and passed as the third argument below.
export interface Context {
  clientId: string;
  clientIp: string;
}

const GENERATIONS_PER_HOUR = 10;
const MAX_HISTORY = 50;
// The GraphQL ImageType enum mapped to the Content-Type the upload form will require.
const CONTENT_TYPES = { JPEG: "image/jpeg", PNG: "image/png" };

// Database row to GraphQL type. The S3 links are signed fresh on every call and last 15 minutes.
async function toGraphQLGeneration(row: Generation) {
  return {
    id: row.id,
    status: row.status,
    genre: row.genre ?? row.requested_genre,
    confidence: row.confidence,
    imageUrl: await signDownloadUrl(imageKey(row.id)),
    audioUrl: row.status === "COMPLETED" ? await signDownloadUrl(audioKey(row.id)) : null,
    errorMessage: row.error_message,
    createdAt: row.created_at.toISOString(),
  };
}

// Someone else's generation looks the same as a missing one, so ids can't be probed.
async function findOwnGeneration(id: string, clientId: string): Promise<Generation> {
  const row = await getGeneration(id);
  if (!row || row.client_id !== clientId) {
    throw new GraphQLError(`Generation ${id} not found`, { extensions: { code: "NOT_FOUND" } });
  }
  return row;
}

// Each resolver gets (parent, args, context). parent is unused because every field here is top level.
export const resolvers = {
  Query: {
    // The browser polls this every 2.5 seconds while a song is being made (GET_GENERATION in
    // Playground.tsx). Someone else's id returns null, the same as an unknown one.
    generation: async (_: unknown, { id }: { id: string }, { clientId }: Context) => {
      const row = await getGeneration(id);
      return row && row.client_id === clientId ? toGraphQLGeneration(row) : null;
    },

    // The History tab (GenerationHistory.tsx). limit is clamped to 1..50 whatever the browser asks for.
    myGenerations: async (_: unknown, { limit }: { limit: number }, { clientId }: Context) => {
      const rows = await listGenerations(clientId, Math.max(1, Math.min(limit, MAX_HISTORY)));
      return Promise.all(rows.map(toGraphQLGeneration));
    },
  },

  Mutation: {
    // Step one of making a song: record a PENDING row and hand back an S3 upload form for the image.
    createGeneration: async (
      _: unknown,
      { genre, imageType }: { genre?: string; imageType: keyof typeof CONTENT_TYPES },
      { clientId, clientIp }: Context,
    ) => {
      // Insert, then count. Two requests at once then both see each other's row, so the
      // limit can be undershot but never exceeded.
      const id = randomUUID();
      await insertGeneration({ id, clientId, clientIp, requestedGenre: genre ?? null });
      if ((await countRecentGenerations(clientId, clientIp)) > GENERATIONS_PER_HOUR) {
        await deleteGeneration(id);
        throw new GraphQLError(`Limit of ${GENERATIONS_PER_HOUR} songs per hour reached`, {
          extensions: { code: "RATE_LIMITED" },
        });
      }
      // The form only accepts this key and content type. The fields object becomes a
      // name/value list because GraphQL has no free-form map type.
      const { url, fields } = await createUploadForm(imageKey(id), CONTENT_TYPES[imageType]);
      return {
        id,
        upload: { url, fields: Object.entries(fields).map(([name, value]) => ({ name, value })) },
      };
    },

    // Check the image really landed in S3, move PENDING to QUEUED exactly once, then send it to SQS.
    // If the send fails the generation goes back to PENDING, so the user can just press start again.
    startGeneration: async (_: unknown, { id }: { id: string }, { clientId }: Context) => {
      // 1. It must be this browser's generation.
      await findOwnGeneration(id, clientId);
      // 2. The image must already be in S3, or the worker would fail on download.
      if (!(await objectExists(imageKey(id)))) {
        throw new GraphQLError("Upload the image before starting", { extensions: { code: "BAD_REQUEST" } });
      }
      // 3. PENDING to QUEUED. Only one of two double clicks can win this update.
      if (!(await markQueued(id))) {
        throw new GraphQLError(`Generation ${id} was already started`, { extensions: { code: "BAD_REQUEST" } });
      }
      // 4. Send the job message the worker will pick up.
      try {
        await enqueueJob(id, clientId);
      } catch (error) {
        await markPending(id);
        throw error;
      }
      return toGraphQLGeneration(await findOwnGeneration(id, clientId));
    },
  },
};
