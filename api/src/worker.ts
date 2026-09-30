// The worker process: its own ECS service, same image as the API. One job at a time, forever:
// sweep stuck generations every 5 minutes, wait for a message, run it through pipeline.ts.
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
  while (!stopping) {
    try {
      if (Date.now() - lastSweep > SWEEP_INTERVAL_MS) {
        lastSweep = Date.now();
        const failed = await failStaleGenerations();
        if (failed > 0) log.warn("failed stale generations", { count: failed });
      }
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
