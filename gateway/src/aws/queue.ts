// The SQS FIFO job queue between the API and the worker.
// Every message shares one group, so jobs run strictly in the order they were started.
// The job id is the deduplication id, so starting the same job twice queues it once.
import { DeleteMessageCommand, ReceiveMessageCommand, SendMessageCommand, SQSClient } from "@aws-sdk/client-sqs";
import { requireEnv } from "../env";

const sqs = new SQSClient({});
const QUEUE_URL = requireEnv("SQS_QUEUE_URL");
const MESSAGE_GROUP = "generations";
const LONG_POLL_SECONDS = 20; // the SQS maximum; waits for a message instead of polling empty

export interface QueuedJob {
  jobId: string;
  receiptHandle: string; // needed to delete the message once the job is done
}

export async function enqueueJob(jobId: string): Promise<void> {
  await sqs.send(new SendMessageCommand({
    QueueUrl: QUEUE_URL,
    MessageBody: JSON.stringify({ jobId }),
    MessageGroupId: MESSAGE_GROUP,
    MessageDeduplicationId: jobId,
  }));
}

/** Waits up to 20 seconds for the next job. Returns null if none arrived. */
export async function receiveJob(): Promise<QueuedJob | null> {
  const { Messages } = await sqs.send(new ReceiveMessageCommand({
    QueueUrl: QUEUE_URL,
    MaxNumberOfMessages: 1,
    WaitTimeSeconds: LONG_POLL_SECONDS,
  }));
  if (!Messages?.length) return null;
  const [message] = Messages;
  return { jobId: JSON.parse(message.Body!).jobId, receiptHandle: message.ReceiptHandle! };
}

export async function deleteJob(job: QueuedJob): Promise<void> {
  await sqs.send(new DeleteMessageCommand({ QueueUrl: QUEUE_URL, ReceiptHandle: job.receiptHandle }));
}
