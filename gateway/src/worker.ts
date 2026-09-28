// worker: pull a job off SQS, run it (pipeline.ts), repeat. one job at a time per task -
// to go faster ECS just runs more of these (autoscaling on queue backlog, see ecs.tf)
import { receiveJob } from "./aws/queue";
import { failStaleJobs, pool } from "./db";
import { log } from "./log";
import { handleMessage } from "./pipeline";

const SWEEP_INTERVAL_MS = 5 * 60 * 1000; // check for lost jobs every 5 min (db.failStaleJobs)
const ERROR_BACKOFF_MS = 5 * 1000; // if SQS/db is down don't spin in a tight loop hammering it

// ECS: SIGTERM -> waits stopTimeout (120s in ecs.tf) -> SIGKILL.
// a song is ~1 min so there's time to finish the current one instead of redoing it
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
