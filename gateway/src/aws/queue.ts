// The SQS FIFO job queue between the API and the worker.
//
// Each browser's jobs share a message group (its client id), so one person's
// songs are made in the order they asked for them, while different people's
// jobs run in parallel on as many workers as are running.
// The job id is the deduplication id, so starting the same job twice queues it once.
import {
  ChangeMessageVisibilityCommand, DeleteMessageCommand, ReceiveMessageCommand, SendMessageCommand, SQSClient,
} from "@aws-sdk/client-sqs";
import { requireEnv } from "../env";

const sqs = new SQSClient({});
const QUEUE_URL = requireEnv("SQS_QUEUE_URL");
const LONG_POLL_SECONDS = 20; // the SQS maximum; waits for a message instead of polling empty

export interface QueuedJob {
  jobId: string;
  receiptHandle: string; // identifies this delivery, to delete or delay the message
  receiveCount: number; // 1 on the first attempt, 2 on the first retry, ...
}

export async function enqueueJob(jobId: string, clientId: string): Promise<void> {
  await sqs.send(new SendMessageCommand({
    QueueUrl: QUEUE_URL,
    MessageBody: JSON.stringify({ jobId }),
    MessageGroupId: clientId,
    MessageDeduplicationId: jobId,
  }));
}

/** Waits up to 20 seconds for the next job. Returns null if none arrived. */
export async function receiveJob(): Promise<QueuedJob | null> {
  const { Messages } = await sqs.send(new ReceiveMessageCommand({
    QueueUrl: QUEUE_URL,
    MaxNumberOfMessages: 1,
    WaitTimeSeconds: LONG_POLL_SECONDS,
    MessageSystemAttributeNames: ["ApproximateReceiveCount"],
  }));
  if (!Messages?.length) return null;
  const [message] = Messages;
  return {
    jobId: JSON.parse(message.Body!).jobId,
    receiptHandle: message.ReceiptHandle!,
    receiveCount: Number(message.Attributes!.ApproximateReceiveCount),
  };
}

/** Removes a finished job from the queue. */
export async function deleteJob(job: QueuedJob): Promise<void> {
  await sqs.send(new DeleteMessageCommand({ QueueUrl: QUEUE_URL, ReceiptHandle: job.receiptHandle }));
}

/**
 * Hands the message back to SQS, visible again after a delay. SQS then delivers it
 * for another attempt, or moves it to the dead-letter queue after the 3rd receive.
 */
export async function releaseJob(job: QueuedJob, delaySeconds: number): Promise<void> {
  await sqs.send(new ChangeMessageVisibilityCommand({
    QueueUrl: QUEUE_URL, ReceiptHandle: job.receiptHandle, VisibilityTimeout: delaySeconds,
  }));
}
