# The FIFO job queue and its dead-letter queue. Visibility and maxReceiveCount must match pipeline.ts.
# startGeneration sends to it (enqueueJob in api/src/aws/queue.ts) and the worker receives from it.

# Messages that failed every attempt end up here, and the dead_letters alarm in monitoring.tf
# emails when one arrives.
resource "aws_sqs_queue" "jobs_dlq" {
  name                      = "${var.app_name}-jobs-dlq.fifo" # a FIFO queue's DLQ must also be FIFO
  fifo_queue                = true
  message_retention_seconds = 14 * 24 * 3600 # the maximum
}

# FIFO keeps each browser's jobs in order, one at a time (MessageGroupId is the client id).
resource "aws_sqs_queue" "jobs" {
  name       = "${var.app_name}-jobs.fifo"
  fifo_queue = true

  # How long a received message stays hidden from other workers. The worker's heartbeat keeps
  # pushing this back while it is busy.
  visibility_timeout_seconds = 120 # must match VISIBILITY_TIMEOUT_SECONDS in pipeline.ts
  # Long polling: an empty receive waits up to 20 seconds for a message instead of returning at once.
  receive_wait_time_seconds = 20

  # After the third receive, SQS moves the message to the dead-letter queue instead.
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.jobs_dlq.arn
    maxReceiveCount     = 3 # must match MAX_ATTEMPTS in pipeline.ts
  })
}
