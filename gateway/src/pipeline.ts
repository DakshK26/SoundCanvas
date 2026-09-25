// What the worker does with one queue message: run the job through the three
// services, then decide the message's fate.
//
//   success          -> COMPLETED, message deleted
//   bad input (4xx)  -> FAILED, message deleted (retrying cannot help)
//   temporary error  -> message reappears in 30 s for another attempt
//   3rd failed try   -> FAILED, message released for SQS to move to the dead-letter queue
import { audioKey, getObject, imageKey, putObject } from "./aws/s3";
import { deleteJob, extendVisibility, QueuedJob, releaseJob } from "./aws/queue";
import { getGeneration, markCompleted, markFailed, startProcessing } from "./db";
import { log } from "./log";
import { composeMidi, extractFeatures, PermanentError, predictGenre, renderAudio } from "./services";

export const MAX_ATTEMPTS = 3; // must match maxReceiveCount in infra/terraform/queue.tf
export const RETRY_DELAY_SECONDS = 30; // gives a restarting service time to come back

// While a job runs, the worker renews the message's visibility every minute. The queue's
// timeout can then stay short (2 minutes, infra/terraform/queue.tf), so if a worker dies
// its job is retried within 2 minutes instead of blocking that browser's FIFO group.
export const VISIBILITY_TIMEOUT_SECONDS = 120;
const HEARTBEAT_MS = 60 * 1000;

/** Runs one step of a job and logs how long it took. */
async function step<T>(jobId: string, name: string, run: () => Promise<T>): Promise<T> {
  const started = Date.now();
  const result = await run();
  log.info("step finished", { jobId, step: name, ms: Date.now() - started });
  return result;
}

/** Turns one uploaded image into a finished song. */
export async function processJob(jobId: string): Promise<void> {
  const job = await getGeneration(jobId);
  if (!job) throw new PermanentError(`Job ${jobId} not found`);

  // False when the job already finished: SQS can deliver a message twice, for
  // example if a worker crashed after finishing but before deleting the message.
  if (!(await startProcessing(jobId))) return;

  const image = await step(jobId, "download", () => getObject(imageKey(jobId)));
  const features = await step(jobId, "features", () => extractFeatures(image));
  const { genre, confidence } = job.requested_genre
    ? { genre: job.requested_genre, confidence: null } // the user picked a genre, so the model is skipped
    : await step(jobId, "predict", () => predictGenre(features));
  const midi = await step(jobId, "compose", () => composeMidi(features, genre));
  const wav = await step(jobId, "render", () => renderAudio(midi, genre));

  await step(jobId, "upload", () => putObject(audioKey(jobId), wav, "audio/wav"));
  await markCompleted(jobId, genre, confidence, features);
}

/** Runs one queue message and decides whether it is done, retried later, or given up on. */
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
      // Visible again now, so the next receive moves it to the dead-letter queue. Waiting out
      // the visibility timeout would hold up this browser's later jobs (FIFO group).
      await releaseJob(message, 0);
    } else {
      await releaseJob(message, RETRY_DELAY_SECONDS);
    }
  } finally {
    clearInterval(heartbeat);
  }
}
