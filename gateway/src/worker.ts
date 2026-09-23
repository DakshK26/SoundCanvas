// The job worker: takes one job at a time off the SQS FIFO queue and runs it
// through cpp-core, ml and audio-producer, saving the song to S3.
//
// A failure inside the pipeline marks the job FAILED and removes the message.
// If the worker itself crashes mid-job, the message becomes visible again after
// the queue's visibility timeout and is retried; after 3 tries SQS moves it to
// the dead-letter queue.
import { audioKey, getObject, imageKey, putObject } from "./aws/s3";
import { deleteJob, receiveJob } from "./aws/queue";
import { getGeneration, markCompleted, markFailed, markProcessing } from "./db";
import { composeMidi, extractFeatures, predictGenre, renderAudio } from "./services";

/** Turns one uploaded image into a finished song. */
async function processJob(jobId: string): Promise<void> {
  const job = await getGeneration(jobId);
  if (!job) throw new Error(`Job ${jobId} not found`);
  await markProcessing(jobId);

  const image = await getObject(imageKey(jobId));
  const features = await extractFeatures(image);
  const { genre, confidence } = job.genre
    ? { genre: job.genre, confidence: null } // the user picked a genre, so the model is skipped
    : await predictGenre(features);
  const midi = await composeMidi(features, genre);
  const wav = await renderAudio(midi, genre);

  await putObject(audioKey(jobId), wav, "audio/wav");
  await markCompleted(jobId, genre, confidence);
}

async function main(): Promise<void> {
  console.log("worker waiting for jobs");
  while (true) {
    const job = await receiveJob();
    if (!job) continue;
    console.log(`job ${job.jobId} started`);
    try {
      await processJob(job.jobId);
      console.log(`job ${job.jobId} completed`);
    } catch (error) {
      console.error(`job ${job.jobId} failed:`, error);
      await markFailed(job.jobId, (error as Error).message);
    }
    await deleteJob(job);
  }
}

main();
