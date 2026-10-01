// One SQS job is one generation: get features, pick a genre, compose, render, then save the WAV.
// Decides whether it is finished, failed for good, or goes back on the queue for a retry.
// worker.ts calls handleMessage for each message; the HTTP calls are in serviceClients.ts.
import { audioKey, getObject, imageKey, putObject } from "./aws/s3";
import { deleteJob, extendVisibility, QueuedJob, releaseJob } from "./aws/queue";
import { getGeneration, markCompleted, markFailed, markProcessing } from "./db";
import { log } from "./log";
import { composeMidi, extractFeatures, PermanentError, predictGenre, renderAudio } from "./serviceClients";

export const MAX_ATTEMPTS = 3; // must match maxReceiveCount in queue.tf
export const RETRY_DELAY_SECONDS = 30;
export const VISIBILITY_TIMEOUT_SECONDS = 120; // must match visibility_timeout_seconds in queue.tf
// Half the visibility timeout, so one missed beat still leaves time for the next.
const HEARTBEAT_MS = 60 * 1000;

// Runs one stage and logs how long it took, so a slow service shows up in the logs.
async function step<T>(generationId: string, name: string, run: () => Promise<T>): Promise<T> {
  const started = Date.now();
  const result = await run();
  log.info("step finished", { generationId, step: name, ms: Date.now() - started });
  return result;
}

// The happy path. Rerunning it is safe: same S3 key, same conditional updates, same song.
export async function processJob(generationId: string): Promise<void> {
  // 1. Load the row. A missing row can never succeed, so it is not retried.
  const generation = await getGeneration(generationId);
  if (!generation) throw new PermanentError(`Generation ${generationId} not found`);

  // 2. Claim it. SQS can deliver the same message twice; a finished generation is skipped.
  if (!(await markProcessing(generationId))) return;

  // 3. The image the browser uploaded, then its 8 colour features from cpp-core /features.
  const image = await step(generationId, "download", () => getObject(imageKey(generationId)));
  const features = await step(generationId, "features", () => extractFeatures(image));
  // 4. The user's genre if they picked one, otherwise ask ml /predict.
  const { genre, confidence } = generation.requested_genre
    ? { genre: generation.requested_genre, confidence: null }
    : await step(generationId, "predict", () => predictGenre(features));
  // 5. MIDI from cpp-core /compose, then a mastered WAV from audio-producer /render.
  const midi = await step(generationId, "compose", () => composeMidi(features, genre));
  const wav = await step(generationId, "render", () => renderAudio(midi, genre));

  // 6. Save the WAV where signDownloadUrl will look for it, then mark the row COMPLETED.
  await step(generationId, "upload", () => putObject(audioKey(generationId), wav, "audio/wav"));
  await markCompleted(generationId, genre, confidence, features);
}

// The retry policy around processJob. receiveCount is how many times SQS has handed out this
// message, so it doubles as the attempt number.
export async function handleMessage(message: QueuedJob): Promise<void> {
  const { generationId, receiveCount: attempt } = message;
  // While this worker is busy, keep pushing the timeout back so no other worker gets the message.
  // If this process dies the heartbeat stops, and the message reappears within 120 seconds.
  const heartbeat = setInterval(() => {
    extendVisibility(message, VISIBILITY_TIMEOUT_SECONDS)
      .catch((error) => log.warn("heartbeat failed", { generationId, error: (error as Error).message }));
  }, HEARTBEAT_MS);

  try {
    // Success: the message is done with, so take it off the queue.
    await processJob(generationId);
    await deleteJob(message);
    log.info("job completed", { generationId, attempt });
  } catch (error) {
    const reason = (error as Error).message;
    log.error("job attempt failed", { generationId, attempt, reason });
    // Bad input fails now. Anything else is retried in 30 seconds, until the last attempt.
    if (error instanceof PermanentError) {
      // The reason is what GenerationHistory and Playground show the user.
      await markFailed(generationId, reason);
      await deleteJob(message);
    } else if (attempt >= MAX_ATTEMPTS) {
      await markFailed(generationId, reason);
      // No delay, so it goes to the DLQ now instead of blocking this browser's FIFO group.
      await releaseJob(message, 0);
    } else {
      // The row stays PROCESSING, and the message comes back in 30 seconds for another try.
      await releaseJob(message, RETRY_DELAY_SECONDS);
    }
  } finally {
    // Stop the heartbeat whatever happened, or it would keep extending a message we gave up on.
    clearInterval(heartbeat);
  }
}
