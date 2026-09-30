# The FIFO job queue and its dead-letter queue. Visibility and maxReceiveCount must match pipeline.ts.

resource "aws_sqs_queue" "jobs_dlq" {
  name                      = "${var.app_name}-jobs-dlq.fifo" # a FIFO queue's DLQ must also be FIFO
  fifo_queue                = true
  message_retention_seconds = 14 * 24 * 3600 # the maximum
}

resource "aws_sqs_queue" "jobs" {
  name       = "${var.app_name}-jobs.fifo"
  fifo_queue = true

  visibility_timeout_seconds = 120 # must match VISIBILITY_TIMEOUT_SECONDS in pipeline.ts
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.jobs_dlq.arn
    maxReceiveCount     = 3 # must match MAX_ATTEMPTS in pipeline.ts
  })
}
