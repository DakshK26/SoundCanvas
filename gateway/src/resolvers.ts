// graphql resolvers. the API only writes rows + queues stuff, never does the slow work itself
import { randomUUID } from "crypto";
import { GraphQLError } from "graphql";
import { audioKey, downloadUrl, imageKey, objectExists, uploadForm } from "./aws/s3";
import { enqueueJob } from "./aws/queue";
import {
  countRecentGenerations, deleteGeneration, Feedback, Generation, getGeneration, insertGeneration, listGenerations,
  markPending, markQueued, setFeedback,
} from "./db";

// built per request in api.ts
export interface Context {
  clientId: string;
  clientIp: string;
}

// each song = ~1 min of fargate compute. 10/hr per browser or ip keeps the bill sane
const SONGS_PER_HOUR = 10;
const MAX_HISTORY = 50;
const CONTENT_TYPES = { JPEG: "image/jpeg", PNG: "image/png" };

// db row -> graphql shape. presigns fresh links every time (old ones expire after 15 min)
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

// someone else's job looks exactly like a missing one, so you can't probe for ids
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
      const rows = await listGenerations(clientId, Math.max(1, Math.min(limit, MAX_HISTORY)));
      return Promise.all(rows.map(toGraphQL));
    },
  },

  Mutation: {
    // step 1 of 2: rate limit, make the row, hand back an S3 upload form
    createGeneration: async (
      _: unknown,
      { genre, imageType }: { genre?: string; imageType: keyof typeof CONTENT_TYPES },
      { clientId, clientIp }: Context,
    ) => {
      // insert THEN count (not count then insert). with count-first, 2 requests at the same
      // time both see 9 and both get in. this way they both see each other's row, so worst
      // case both get rejected - can undershoot the limit but never go over it
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

    // step 2: browser uploaded to S3, now actually queue it.
    // (2 steps bc the worker needs the image to already be there when it picks the job up)
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
        await markPending(jobId); // SQS send failed -> undo so they can just hit start again
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
