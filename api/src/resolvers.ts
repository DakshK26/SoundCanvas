// What each GraphQL query and mutation does. Everything is scoped to the caller's client id, and
// nothing here is slow: starting a generation only puts a job on the queue for a worker.
import { randomUUID } from "crypto";
import { GraphQLError } from "graphql";
import { audioKey, createUploadForm, imageKey, objectExists, signDownloadUrl } from "./aws/s3";
import { enqueueJob } from "./aws/queue";
import {
  countRecentGenerations, deleteGeneration, Generation, getGeneration, insertGeneration, listGenerations,
  markPending, markQueued,
} from "./db";

export interface Context {
  clientId: string;
  clientIp: string;
}

const GENERATIONS_PER_HOUR = 10;
const MAX_HISTORY = 50;
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

export const resolvers = {
  Query: {
    // The browser polls this every 2.5 seconds while a song is being made.
    generation: async (_: unknown, { id }: { id: string }, { clientId }: Context) => {
      const row = await getGeneration(id);
      return row && row.client_id === clientId ? toGraphQLGeneration(row) : null;
    },

    myGenerations: async (_: unknown, { limit }: { limit: number }, { clientId }: Context) => {
      const rows = await listGenerations(clientId, Math.max(1, Math.min(limit, MAX_HISTORY)));
      return Promise.all(rows.map(toGraphQLGeneration));
    },
  },

  Mutation: {
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
      const { url, fields } = await createUploadForm(imageKey(id), CONTENT_TYPES[imageType]);
      return {
        id,
        upload: { url, fields: Object.entries(fields).map(([name, value]) => ({ name, value })) },
      };
    },

    // Check the image really landed in S3, move PENDING to QUEUED exactly once, then send it to SQS.
    // If the send fails the generation goes back to PENDING, so the user can just press start again.
    startGeneration: async (_: unknown, { id }: { id: string }, { clientId }: Context) => {
      await findOwnGeneration(id, clientId);
      if (!(await objectExists(imageKey(id)))) {
        throw new GraphQLError("Upload the image before starting", { extensions: { code: "BAD_REQUEST" } });
      }
      if (!(await markQueued(id))) {
        throw new GraphQLError(`Generation ${id} was already started`, { extensions: { code: "BAD_REQUEST" } });
      }
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
