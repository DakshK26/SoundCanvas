# Three CloudWatch alarms emailed through SNS: a message in the DLQ, a job waiting over 10 minutes,
# or 5 or more API 5xx errors in 5 minutes.
# Each alarm watches a metric AWS already publishes for the queues in queue.tf and the ALB in network.tf.

# ---- Where alarms go ----

resource "aws_sns_topic" "alarms" {
  name = "${var.app_name}-alarms"
}

# count = 0 skips the subscription when no alarm_email is set in variables.tf.
resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email" # nothing is sent until the confirmation link in the first email is clicked
  endpoint  = var.alarm_email
}

# ---- Alarms ----
# All three check one 5-minute window (period 300 s, evaluation_periods 1).

# Any message in the dead-letter queue means a generation failed all 3 attempts in pipeline.ts.
resource "aws_cloudwatch_metric_alarm" "dead_letters" {
  alarm_name          = "${var.app_name}-dead-letters"
  alarm_description   = "A job failed every retry and was moved to the dead-letter queue."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = aws_sqs_queue.jobs_dlq.name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

# The oldest message waiting over 10 minutes means the workers are down or not keeping up.
resource "aws_cloudwatch_metric_alarm" "queue_backlog" {
  alarm_name          = "${var.app_name}-queue-backlog"
  alarm_description   = "The oldest waiting job has been queued for over 10 minutes."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  dimensions          = { QueueName = aws_sqs_queue.jobs.name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 600 # seconds
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

# 5xx responses from the api task, counted by the load balancer. Expected GraphQL errors
# (NOT_FOUND, RATE_LIMITED) are not 5xx, so they do not count. No traffic is treated as fine.
resource "aws_cloudwatch_metric_alarm" "api_errors" {
  alarm_name          = "${var.app_name}-api-errors"
  alarm_description   = "The GraphQL API returned 5 or more server errors in 5 minutes."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  dimensions          = { LoadBalancer = aws_lb.api.arn_suffix, TargetGroup = aws_lb_target_group.api.arn_suffix }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 5
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
}
