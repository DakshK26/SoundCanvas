// The job worker: takes jobs off the SQS FIFO queue one at a time and runs
// each through cpp-core, ml and audio-producer (see pipeline.ts).
// ECS runs more copies of this container when the queue backs up.
import { receiveJob } from "./aws/queue";
import { handleMessage } from "./pipeline";

async function main(): Promise<void> {
  console.log("worker waiting for jobs");
  while (true) {
    const message = await receiveJob();
    if (message) await handleMessage(message);
  }
}

main();
