// What the worker does with one queue message: run the job through the three
// services, then decide the message's fate.
//
//   success          -> COMPLETED, message deleted
//   bad input (4xx)  -> FAILED, message deleted (retrying cannot help)
//   temporary error  -> message reappears in 30 s for another attempt
//   3rd failed try   -> FAILED, message left for SQS to move to the dead-letter queue
import { audioKey, getObject, imageKey, putObject } from "./aws/s3";
import { deleteJob, QueuedJob, retryLater } from "./aws/queue";
import { getGeneration, markCompleted, markFailed, startProcessing } from "./db";
import { composeMidi, extractFeatures, PermanentError, predictGenre, renderAudio } from "./services";

export const MAX_ATTEMPTS = 3; // must match maxReceiveCount in infra/terraform/queue.tf
export const RETRY_DELAY_SECONDS = 30; // gives a restarting service time to come back

/** Turns one uploaded image into a finished song. */
export async function processJob(jobId: string): Promise<void> {
  const job = await getGeneration(jobId);
  if (!job) throw new PermanentError(`Job ${jobId} not found`);

  // False when the job already finished: SQS can deliver a message twice, for
  // example if a worker crashed after finishing but before deleting the message.
  if (!(await startProcessing(jobId))) return;

  const image = await getObject(imageKey(jobId));
  const features = await extractFeatures(image);
  const { genre, confidence } = job.requested_genre
    ? { genre: job.requested_genre, confidence: null } // the user picked a genre, so the model is skipped
    : await predictGenre(features);
  const midi = await composeMidi(features, genre);
  const wav = await renderAudio(midi, genre);

  await putObject(audioKey(jobId), wav, "audio/wav");
  await markCompleted(jobId, genre, confidence, features);
}

/** Runs one queue message and decides whether it is done, retried later, or given up on. */
export async function handleMessage(message: QueuedJob): Promise<void> {
  try {
    await processJob(message.jobId);
    await deleteJob(message);
    console.log(`job ${message.jobId} completed`);
  } catch (error) {
    const reason = (error as Error).message;
    console.error(`job ${message.jobId} attempt ${message.receiveCount} failed: ${reason}`);
    if (error instanceof PermanentError) {
      await markFailed(message.jobId, reason);
      await deleteJob(message);
    } else if (message.receiveCount >= MAX_ATTEMPTS) {
      await markFailed(message.jobId, reason);
    } else {
      await retryLater(message, RETRY_DELAY_SECONDS);
    }
  }
}
