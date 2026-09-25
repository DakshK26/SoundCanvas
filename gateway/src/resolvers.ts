// GraphQL resolvers. The API records jobs and queues them; the worker does the work.
import { randomUUID } from "crypto";
import { GraphQLError } from "graphql";
import { audioKey, downloadUrl, imageKey, objectExists, uploadForm } from "./aws/s3";
import { enqueueJob } from "./aws/queue";
import {
  countRecentGenerations, deleteGeneration, Feedback, Generation, getGeneration, insertGeneration, listGenerations,
  markPending, markQueued, setFeedback,
} from "./db";

/** Who is calling, taken from each request in api.ts. */
export interface Context {
  clientId: string;
  clientIp: string;
}

// Each song costs about a minute of compute, so one browser or IP address gets 10 per hour.
const SONGS_PER_HOUR = 10;
const MAX_HISTORY = 50;
const CONTENT_TYPES = { JPEG: "image/jpeg", PNG: "image/png" };

/** Converts a database row to the GraphQL Generation type, with fresh download links. */
async function toGraphQL(row: Generation) {
  return {
    id: row.id,
    status: row.status,
    genre: row.genre ?? row.requested_genre,
    confidence: row.confidence,
    feedback: row.feedback,
    imageUrl: await downloadUrl(imageKey(row.id)),
    audioUrl: row.status === "COMPLETED" ? await downloadUrl(audioKey(row.id)) : null,
    errorMessage: row.error_message,
    createdAt: row.created_at.toISOString(),
  };
}

/** Loads a job, treating another browser's job as not found. */
async function findOwnJob(jobId: string, clientId: string): Promise<Generation> {
  const row = await getGeneration(jobId);
  if (!row || row.client_id !== clientId) {
    throw new GraphQLError(`Job ${jobId} not found`, { extensions: { code: "NOT_FOUND" } });
  }
  return row;
}

export const resolvers = {
  Query: {
    generation: async (_: unknown, { jobId }: { jobId: string }, { clientId }: Context) => {
      const row = await getGeneration(jobId);
      return row && row.client_id === clientId ? toGraphQL(row) : null;
    },

    myGenerations: async (_: unknown, { limit }: { limit: number }, { clientId }: Context) => {
      const rows = await listGenerations(clientId, Math.min(limit, MAX_HISTORY));
      return Promise.all(rows.map(toGraphQL));
    },
  },

  Mutation: {
    /** Step 1: check the rate limit, record the job, and return an upload form for the image. */
    createGeneration: async (
      _: unknown,
      { genre, imageType }: { genre?: string; imageType: keyof typeof CONTENT_TYPES },
      { clientId, clientIp }: Context,
    ) => {
      // Insert first, then count: two simultaneous requests both see each other's row, so the
      // limit can only ever be undershot, never exceeded (count-then-insert lets both through).
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

    /** Step 2: once the image is in S3, put the job on the queue. */
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
        await markPending(jobId); // back to PENDING so the user can press start again
        throw error;
      }
      return toGraphQL(await findOwnJob(jobId, clientId));
    },

    rateGeneration: async (
      _: unknown,
      { jobId, feedback }: { jobId: string; feedback: Feedback },
      { clientId }: Context,
    ) => {
      if (!(await setFeedback(jobId, clientId, feedback))) {
        throw new GraphQLError("Only your own finished songs can be rated", { extensions: { code: "BAD_REQUEST" } });
      }
      return toGraphQL(await findOwnJob(jobId, clientId));
    },
  },
};
