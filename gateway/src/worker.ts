// The job worker: takes jobs off the SQS FIFO queue one at a time and runs
// each through cpp-core, ml and audio-producer (see pipeline.ts).
// ECS runs more copies of this container when the queue backs up.
import { receiveJob } from "./aws/queue";
import { failStaleJobs, pool } from "./db";
import { log } from "./log";
import { handleMessage } from "./pipeline";

const SWEEP_INTERVAL_MS = 5 * 60 * 1000; // how often to look for lost jobs (see failStaleJobs)
const ERROR_BACKOFF_MS = 5 * 1000; // pause after an SQS or database error instead of spinning

// ECS sends SIGTERM when it scales in or deploys, then waits stopTimeout (120 s, ecs.tf)
// before killing the task. Finishing the current job in that window means it is not redone.
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
        const failed = await failStaleJobs();
        if (failed > 0) log.warn("failed stale jobs", { count: failed });
      }
      const message = await receiveJob();
      if (message) await handleMessage(message);
    } catch (error) {
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
