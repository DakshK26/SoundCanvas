import { StorageService } from "../services/storage";
import { insertGeneration, updateGenerationStatus } from "../db";
import { OrchestratorService } from "../services/orchestrator";
import { v4 as uuidv4 } from "uuid";
import Logger, { LogEvent } from "../utils/logger";

export const Mutation = {
  // ============================================================================
  // Phase 10+: S3-based workflow
  // ============================================================================
  createGeneration: async (
    _: unknown,
    args: { input: { genreOverride?: string; mode?: string } },
    context: any
  ) => {
    const jobId = uuidv4();
    const userId = context.user?.id || 'default-user';
    const genre = args.input.genreOverride || 'auto';
    const mode = args.input.mode || 'model';

    Logger.info('Creating new generation', {
      jobId,
      userId,
      event: LogEvent.JOB_CREATED,
      metadata: { genre, mode },
    });

    // Generate S3 pre-signed upload URL
    const storage = new StorageService();
    const imageKey = storage.getImageKey(userId, jobId);
    const uploadUrl = await storage.getImageUploadUrl(userId, jobId);

    // Create database record
    await insertGeneration({
      id: jobId,
      user_id: userId,
      image_key: imageKey,
      genre: genre,
      mode: mode as 'heuristic' | 'model',
    });

    Logger.info('Generation record created, awaiting image upload', {
      jobId,
      userId,
      metadata: { imageKey },
    });

    return {
      jobId,
      imageUploadUrl: uploadUrl,
      imageId: imageKey,
    };
  },

  startGeneration: async (
    _: unknown,
    args: { jobId: string },
    context: any
  ) => {
    const { jobId } = args;
    const userId = context.user?.id || 'default-user';

    Logger.info('Starting generation pipeline', {
      jobId,
      userId,
      event: LogEvent.JOB_STARTED,
    });

    // Update status to RUNNING
    await updateGenerationStatus(jobId, 'RUNNING');

    // Trigger async processing (fire and forget)
    processGeneration(jobId, userId).catch(async (err) => {
      Logger.error(`Generation failed: ${err.message}`, {
        jobId,
        userId,
        event: LogEvent.JOB_FAILED,
        metadata: { error: err.stack },
      });
      await updateGenerationStatus(jobId, 'FAILED', {
        error_message: err.message || 'Unknown error',
      });
    });

    return { success: true };
  },
};

// ============================================================================
// Async generation pipeline
// ============================================================================
async function processGeneration(jobId: string, userId: string) {
  const orchestrator = new OrchestratorService();
  await orchestrator.processGeneration(jobId, userId);
}