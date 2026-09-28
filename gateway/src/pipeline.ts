// one queue message -> run the job thru the 3 services -> decide what happens to the message
//
// cheat sheet for how each outcome ends up:
//   worked           -> COMPLETED, delete msg
//   bad input (4xx)  -> FAILED, delete msg (retrying the same bad image won't fix it)
//   5xx / timeout    -> let it reappear in 30s and try again
//   3rd fail         -> FAILED, release it so SQS moves it to the DLQ
import { audioKey, getObject, imageKey, putObject } from "./aws/s3";
import { deleteJob, extendVisibility, QueuedJob, releaseJob } from "./aws/queue";
import { getGeneration, markCompleted, markFailed, startProcessing } from "./db";
import { log } from "./log";
import { composeMidi, extractFeatures, PermanentError, predictGenre, renderAudio } from "./services";

export const MAX_ATTEMPTS = 3; // keep in sync w/ maxReceiveCount in queue.tf!!
export const RETRY_DELAY_SECONDS = 30; // time for a crashed service to restart

// heartbeat: had visibility at 10 min originally, so a dead worker = 10 min before anyone
// retried (and it blocked that browser's whole FIFO group). now it's 2 min and the worker
// bumps it every 60s while it's alive. worker dies -> bumps stop -> retried within 2 min
export const VISIBILITY_TIMEOUT_SECONDS = 120;
const HEARTBEAT_MS = 60 * 1000;

// wraps each step so the logs show how long it took (CloudWatch Insights can avg `ms` by `step`)
async function step<T>(jobId: string, name: string, run: () => Promise<T>): Promise<T> {
  const started = Date.now();
  const result = await run();
  log.info("step finished", { jobId, step: name, ms: Date.now() - started });
  return result;
}

// image in S3 -> song in S3
export async function processJob(jobId: string): Promise<void> {
  const job = await getGeneration(jobId);
  if (!job) throw new PermanentError(`Job ${jobId} not found`);

  // SQS is at-least-once, so the same msg can show up twice (e.g. worker finished but died
  // before deleteJob). startProcessing returns false if it's already done -> just skip
  if (!(await startProcessing(jobId))) return;

  const image = await step(jobId, "download", () => getObject(imageKey(jobId)));
  const features = await step(jobId, "features", () => extractFeatures(image));
  const { genre, confidence } = job.requested_genre
    ? { genre: job.requested_genre, confidence: null } // user picked one, no need for the model
    : await step(jobId, "predict", () => predictGenre(features));
  const midi = await step(jobId, "compose", () => composeMidi(features, genre));
  const wav = await step(jobId, "render", () => renderAudio(midi, genre));

  await step(jobId, "upload", () => putObject(audioKey(jobId), wav, "audio/wav"));
  await markCompleted(jobId, genre, confidence, features);
}

// the worker loop calls this for every message it gets
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
      // release w/ 0 delay so the next receive pushes it to the DLQ right away.
      // if I just waited out the timeout, this browser's other jobs sit stuck behind it (FIFO)
      await releaseJob(message, 0);
    } else {
      await releaseJob(message, RETRY_DELAY_SECONDS);
    }
  } finally {
    clearInterval(heartbeat);
  }
}
