// The SQS FIFO queue between startGeneration (sends) and the workers (receive, delete, release).
// A job message only holds the generation id; everything else lives in MySQL.
import {
  ChangeMessageVisibilityCommand, DeleteMessageCommand, ReceiveMessageCommand, SendMessageCommand, SQSClient,
} from "@aws-sdk/client-sqs";
import { requireEnv } from "../env";

const sqs = new SQSClient({});
const QUEUE_URL = requireEnv("SQS_QUEUE_URL");
const LONG_POLL_SECONDS = 20; // the SQS maximum

export interface QueuedJob {
  generationId: string;
  receiptHandle: string;
  receiveCount: number;
}

// The group id keeps one browser's jobs in order and on one worker at a time. The dedup id makes
// sending the same generation again within SQS's five-minute window a no-op.
export async function enqueueJob(generationId: string, clientId: string): Promise<void> {
  await sqs.send(new SendMessageCommand({
    QueueUrl: QUEUE_URL,
    MessageBody: JSON.stringify({ generationId }),
    MessageGroupId: clientId,
    MessageDeduplicationId: generationId,
  }));
}

// Long polls for one message. ApproximateReceiveCount is how many times SQS has handed this
// message out, and the pipeline uses it as the attempt number.
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
    generationId: JSON.parse(message.Body!).generationId,
    receiptHandle: message.ReceiptHandle!,
    receiveCount: Number(message.Attributes!.ApproximateReceiveCount),
  };
}

// After a success or a permanent failure the message has to leave the queue, or it will be retried.
export async function deleteJob(job: QueuedJob): Promise<void> {
  await sqs.send(new DeleteMessageCommand({ QueueUrl: QUEUE_URL, ReceiptHandle: job.receiptHandle }));
}

// A retry is just making the message visible again after a delay. Releasing and extending are the
// same SQS call; the two names say what the caller means.
export async function releaseJob(job: QueuedJob, delaySeconds: number): Promise<void> {
  await setVisibility(job, delaySeconds);
}

export async function extendVisibility(job: QueuedJob, seconds: number): Promise<void> {
  await setVisibility(job, seconds);
}

async function setVisibility(job: QueuedJob, seconds: number): Promise<void> {
  await sqs.send(new ChangeMessageVisibilityCommand({
    QueueUrl: QUEUE_URL, ReceiptHandle: job.receiptHandle, VisibilityTimeout: seconds,
  }));
}
