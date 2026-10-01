// The worker process: its own ECS service, same image as the API. One job at a time, forever:
// sweep stuck generations every 5 minutes, wait for a message, run it through pipeline.ts.
// Started with `npm run worker`; the worker service in ecs.tf and docker-compose.yml run that command.
import { receiveJob } from "./aws/queue";
import { failStaleGenerations, pool } from "./db";
import { log } from "./log";
import { handleMessage } from "./pipeline";

const SWEEP_INTERVAL_MS = 5 * 60 * 1000;
const ERROR_BACKOFF_MS = 5 * 1000;

// ECS waits stopTimeout (120 s in ecs.tf) after SIGTERM, enough to finish the current song.
let stopping = false;
process.on("SIGTERM", () => {
  stopping = true;
  log.info("SIGTERM received: finishing the current job, then exiting");
});

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function main(): Promise<void> {
  log.info("worker waiting for jobs");
  let lastSweep = 0;
  // The flag is only checked between messages, so a song in progress always finishes.
  while (!stopping) {
    try {
      // Every 5 minutes, fail anything stuck in QUEUED or PROCESSING for over an hour (db.ts).
      if (Date.now() - lastSweep > SWEEP_INTERVAL_MS) {
        lastSweep = Date.now();
        const failed = await failStaleGenerations();
        if (failed > 0) log.warn("failed stale generations", { count: failed });
      }
      // Waits up to 20 seconds for a message (long polling), so an idle loop is cheap.
      const message = await receiveJob();
      if (message) await handleMessage(message);
    } catch (error) {
      // SQS or MySQL being briefly unreachable shouldn't kill the process: log, wait, carry on.
      log.error("worker loop error", { error: (error as Error).message });
      await sleep(ERROR_BACKOFF_MS);
    }
  }
  await pool.end();
}

main().catch((error) => {
  log.error("worker crashed", { error: (error as Error).message });
  process.exit(1);
});
