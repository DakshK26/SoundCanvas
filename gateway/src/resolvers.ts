// GraphQL resolvers. The API only records jobs and queues them; the worker does the work.
import { randomUUID } from "crypto";
import { GraphQLError } from "graphql";
import { audioKey, downloadUrl, imageKey, uploadUrl } from "./aws/s3";
import { enqueueJob } from "./aws/queue";
import { Generation, getGeneration, insertGeneration, markQueued } from "./db";

/** Converts a database row to the GraphQL Generation type, with fresh download URLs. */
async function toGraphQL(row: Generation) {
  return {
    id: row.id,
    status: row.status,
    genre: row.genre,
    confidence: row.confidence,
    imageUrl: await downloadUrl(imageKey(row.id)),
    audioUrl: row.status === "COMPLETED" ? await downloadUrl(audioKey(row.id)) : null,
    errorMessage: row.error_message,
    createdAt: row.created_at.toISOString(),
  };
}

export const resolvers = {
  Query: {
    generation: async (_: unknown, { jobId }: { jobId: string }) => {
      const row = await getGeneration(jobId);
      return row && toGraphQL(row);
    },
  },

  Mutation: {
    /** Step 1: record the job and hand back a URL for the browser to upload the image to. */
    createGeneration: async (_: unknown, { genre }: { genre?: string }) => {
      const jobId = randomUUID();
      await insertGeneration(jobId, genre ?? null);
      return { jobId, uploadUrl: await uploadUrl(imageKey(jobId)) };
    },

    /** Step 2: once the image is uploaded, put the job on the queue. */
    startGeneration: async (_: unknown, { jobId }: { jobId: string }) => {
      if (!(await markQueued(jobId))) {
        throw new GraphQLError(`Job ${jobId} does not exist or was already started`);
      }
      await enqueueJob(jobId);
      return toGraphQL((await getGeneration(jobId))!);
    },
  },
};
