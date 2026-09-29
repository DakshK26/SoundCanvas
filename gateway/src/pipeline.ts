import { audioKey, getObject, imageKey, putObject } from "./aws/s3";
import { deleteJob, extendVisibility, QueuedJob, releaseJob } from "./aws/queue";
import { getGeneration, markCompleted, markFailed, startProcessing } from "./db";
import { log } from "./log";
import { composeMidi, extractFeatures, PermanentError, predictGenre, renderAudio } from "./services";

export const MAX_ATTEMPTS = 3; // must match maxReceiveCount in queue.tf
export const RETRY_DELAY_SECONDS = 30;
export const VISIBILITY_TIMEOUT_SECONDS = 120; // must match visibility_timeout_seconds in queue.tf
const HEARTBEAT_MS = 60 * 1000;

async function step<T>(jobId: string, name: string, run: () => Promise<T>): Promise<T> {
  const started = Date.now();
  const result = await run();
  log.info("step finished", { jobId, step: name, ms: Date.now() - started });
  return result;
}

export async function processJob(jobId: string): Promise<void> {
  const job = await getGeneration(jobId);
  if (!job) throw new PermanentError(`Job ${jobId} not found`);

  // SQS can deliver the same message twice; a finished job is skipped.
  if (!(await startProcessing(jobId))) return;

  const image = await step(jobId, "download", () => getObject(imageKey(jobId)));
  const features = await step(jobId, "features", () => extractFeatures(image));
  const { genre, confidence } = job.requested_genre
    ? { genre: job.requested_genre, confidence: null }
    : await step(jobId, "predict", () => predictGenre(features));
  const midi = await step(jobId, "compose", () => composeMidi(features, genre));
  const wav = await step(jobId, "render", () => renderAudio(midi, genre));

  await step(jobId, "upload", () => putObject(audioKey(jobId), wav, "audio/wav"));
  await markCompleted(jobId, genre, confidence, features);
}

export async function handleMessage(message: QueuedJob): Promise<void> {
  const { jobId, receiveCount: attempt } = message;
  const heartbeat = setInterval(() => {
    extendVisibility(message, VISIBILITY_TIMEOUT_SECONDS)
      .catch((error) => log.warn("heartbeat failed", { jobId, error: (error as Error).message }));
  }, HEARTBEAT_MS);

  try {
    await processJob(jobId);
    await deleteJob(message);
    log.info("job completed", { jobId, attempt });
  } catch (error) {
    const reason = (error as Error).message;
    log.error("job attempt failed", { jobId, attempt, reason });
    if (error instanceof PermanentError) {
      await markFailed(jobId, reason);
      await deleteJob(message);
    } else if (attempt >= MAX_ATTEMPTS) {
      await markFailed(jobId, reason);
      // No delay, so it goes to the DLQ now instead of blocking this browser's FIFO group.
      await releaseJob(message, 0);
    } else {
      await releaseJob(message, RETRY_DELAY_SECONDS);
    }
  } finally {
    clearInterval(heartbeat);
  }
}
