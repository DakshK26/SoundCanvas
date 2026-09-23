# The job queue: SQS FIFO between the gateway API (sends) and the workers (receive).
# FIFO keeps each browser's jobs in order (one message group per browser) and
# drops duplicate sends of the same job id.

resource "aws_sqs_queue" "jobs_dlq" {
  name                      = "${var.app_name}-jobs-dlq.fifo" # FIFO queue names must end in .fifo
  fifo_queue                = true
  message_retention_seconds = 14 * 24 * 3600 # the SQS maximum, 14 days, to leave time to inspect
}

resource "aws_sqs_queue" "jobs" {
  name       = "${var.app_name}-jobs.fifo"
  fifo_queue = true

  # A song takes about a minute, and the worker's service timeouts cap a job at
  # 8 minutes. If a message is not deleted within 10 minutes, the worker is
  # assumed to have crashed and the message is handed out again.
  visibility_timeout_seconds = 600
  receive_wait_time_seconds  = 20 # long polling, matching the worker

  # After 3 failed attempts, a message moves to the dead-letter queue
  # (MAX_ATTEMPTS in gateway/src/pipeline.ts must match).
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.jobs_dlq.arn
    maxReceiveCount     = 3
  })
}
