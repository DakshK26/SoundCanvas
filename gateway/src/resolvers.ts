// What each GraphQL query and mutation does. Everything is scoped to the caller's client id, and
// nothing here is slow: starting a job only puts a message on the queue for a worker.
import { randomUUID } from "crypto";
import { GraphQLError } from "graphql";
import { audioKey, downloadUrl, imageKey, objectExists, uploadForm } from "./aws/s3";
import { enqueueJob } from "./aws/queue";
import {
  countRecentGenerations, deleteGeneration, Generation, getGeneration, insertGeneration, listGenerations,
  markPending, markQueued,
} from "./db";

export interface Context {
  clientId: string;
  clientIp: string;
}

const SONGS_PER_HOUR = 10;
const MAX_HISTORY = 50;
const CONTENT_TYPES = { JPEG: "image/jpeg", PNG: "image/png" };

// Database row to GraphQL type. The S3 links are signed fresh on every call and last 15 minutes.
async function toGraphQL(row: Generation) {
  return {
    id: row.id,
    status: row.status,
    genre: row.genre ?? row.requested_genre,
    confidence: row.confidence,
    imageUrl: await downloadUrl(imageKey(row.id)),
    audioUrl: row.status === "COMPLETED" ? await downloadUrl(audioKey(row.id)) : null,
    errorMessage: row.error_message,
    createdAt: row.created_at.toISOString(),
  };
}

// Someone else's job looks the same as a missing one, so ids can't be probed.
async function findOwnJob(jobId: string, clientId: string): Promise<Generation> {
  const row = await getGeneration(jobId);
  if (!row || row.client_id !== clientId) {
    throw new GraphQLError(`Job ${jobId} not found`, { extensions: { code: "NOT_FOUND" } });
  }
  return row;
}

export const resolvers = {
  Query: {
    // The browser polls this every 2.5 seconds while a job runs.
    generation: async (_: unknown, { jobId }: { jobId: string }, { clientId }: Context) => {
      const row = await getGeneration(jobId);
      return row && row.client_id === clientId ? toGraphQL(row) : null;
    },

    myGenerations: async (_: unknown, { limit }: { limit: number }, { clientId }: Context) => {
      const rows = await listGenerations(clientId, Math.max(1, Math.min(limit, MAX_HISTORY)));
      return Promise.all(rows.map(toGraphQL));
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
      const jobId = randomUUID();
      await insertGeneration({ id: jobId, clientId, clientIp, requestedGenre: genre ?? null });
      if ((await countRecentGenerations(clientId, clientIp)) > SONGS_PER_HOUR) {
        await deleteGeneration(jobId);
        throw new GraphQLError(`Limit of ${SONGS_PER_HOUR} songs per hour reached`, {
          extensions: { code: "RATE_LIMITED" },
        });
      }
      const { url, fields } = await uploadForm(imageKey(jobId), CONTENT_TYPES[imageType]);
      return {
        jobId,
        upload: { url, fields: Object.entries(fields).map(([name, value]) => ({ name, value })) },
      };
    },

    // Check the image really landed in S3, move PENDING to QUEUED exactly once, then send it to SQS.
    // If the send fails the job goes back to PENDING, so the user can just press start again.
    startGeneration: async (_: unknown, { jobId }: { jobId: string }, { clientId }: Context) => {
      await findOwnJob(jobId, clientId);
      if (!(await objectExists(imageKey(jobId)))) {
        throw new GraphQLError("Upload the image before starting the job", { extensions: { code: "BAD_REQUEST" } });
      }
      if (!(await markQueued(jobId))) {
        throw new GraphQLError(`Job ${jobId} was already started`, { extensions: { code: "BAD_REQUEST" } });
      }
      try {
        await enqueueJob(jobId, clientId);
      } catch (error) {
        await markPending(jobId);
        throw error;
      }
      return toGraphQL(await findOwnJob(jobId, clientId));
    },
  },
};
