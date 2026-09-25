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

  # While a worker runs a job it extends this every minute (the heartbeat in
  # gateway/src/pipeline.ts). If the worker dies, the heartbeat stops and the
  # message is handed out again within 2 minutes, instead of waiting out a long fixed timeout.
  visibility_timeout_seconds = 120 # VISIBILITY_TIMEOUT_SECONDS in pipeline.ts must match
  receive_wait_time_seconds  = 20  # long polling, matching the worker

  # After 3 failed attempts, a message moves to the dead-letter queue
  # (MAX_ATTEMPTS in gateway/src/pipeline.ts must match).
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.jobs_dlq.arn
    maxReceiveCount     = 3
  })
}
