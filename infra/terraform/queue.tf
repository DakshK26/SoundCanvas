# job queue. api sends, workers receive. FIFO instead of standard bc:
#   - message group = browser -> each browser's jobs go in order, 1 at a time
#   - dedup id = job id -> a double send of the same job gets dropped (5 min window)

resource "aws_sqs_queue" "jobs_dlq" {
  name                      = "${var.app_name}-jobs-dlq.fifo" # has to end in .fifo. also a FIFO queue's DLQ has to be FIFO
  fifo_queue                = true
  message_retention_seconds = 14 * 24 * 3600 # 14 days = max, so there's time to look at what broke
}

resource "aws_sqs_queue" "jobs" {
  name       = "${var.app_name}-jobs.fifo"
  fifo_queue = true

  # short timeout + heartbeat: worker bumps visibility every 60s while it works (pipeline.ts).
  # worker dies -> heartbeat stops -> job is back on the queue within 2 min.
  # (vs one long fixed timeout where a dead worker's job sits hidden the whole time)
  visibility_timeout_seconds = 120 # must match VISIBILITY_TIMEOUT_SECONDS in pipeline.ts
  receive_wait_time_seconds  = 20  # long polling, same as the worker

  # 3 receives -> DLQ. MAX_ATTEMPTS in pipeline.ts has to match!!
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.jobs_dlq.arn
    maxReceiveCount     = 3
  })
}
