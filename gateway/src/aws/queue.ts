// SQS FIFO queue, API -> worker
//
// notes on FIFO:
// - MessageGroupId is required. using the browser's clientId -> one person's songs go in
//   order + only 1 at a time, but different people run in parallel. free fairness basically
// - MessageDeduplicationId = jobId, so double-clicking start only queues it once
//   (dedup window is 5 min, which is plenty for that)
import {
  ChangeMessageVisibilityCommand, DeleteMessageCommand, ReceiveMessageCommand, SendMessageCommand, SQSClient,
} from "@aws-sdk/client-sqs";
import { requireEnv } from "../env";

const sqs = new SQSClient({});
const QUEUE_URL = requireEnv("SQS_QUEUE_URL");
const LONG_POLL_SECONDS = 20; // max allowed. long polling = way fewer empty receives (and cheaper)

export interface QueuedJob {
  jobId: string;
  receiptHandle: string; // NOT the message id - it's per delivery, need it to delete/change visibility
  receiveCount: number; // 1 = first try, 2 = first retry...
}

export async function enqueueJob(jobId: string, clientId: string): Promise<void> {
  await sqs.send(new SendMessageCommand({
    QueueUrl: QUEUE_URL,
    MessageBody: JSON.stringify({ jobId }),
    MessageGroupId: clientId,
    MessageDeduplicationId: jobId,
  }));
}

// blocks up to 20s, null if nothing came in
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

// SQS never deletes on its own after a receive, you have to do it once the job's done
export async function deleteJob(job: QueuedJob): Promise<void> {
  await sqs.send(new DeleteMessageCommand({ QueueUrl: QUEUE_URL, ReceiptHandle: job.receiptHandle }));
}

// "give it back": visible again after delaySeconds. after the 3rd receive the redrive
// policy moves it to the DLQ instead of delivering it again
export async function releaseJob(job: QueuedJob, delaySeconds: number): Promise<void> {
  await setVisibility(job, delaySeconds);
}

// heartbeat - same API call as releaseJob, just used to keep it hidden longer.
// two names so pipeline.ts reads right
export async function extendVisibility(job: QueuedJob, seconds: number): Promise<void> {
  await setVisibility(job, seconds);
}

async function setVisibility(job: QueuedJob, seconds: number): Promise<void> {
  await sqs.send(new ChangeMessageVisibilityCommand({
    QueueUrl: QUEUE_URL, ReceiptHandle: job.receiptHandle, VisibilityTimeout: seconds,
  }));
}
