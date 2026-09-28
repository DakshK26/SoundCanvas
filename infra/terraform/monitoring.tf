# alarms -> SNS -> my email. only 3, one per way a user actually gets let down:
#   1. job failed for good (DLQ)   2. jobs stuck waiting   3. api 5xx

resource "aws_sns_topic" "alarms" {
  name = "${var.app_name}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email" # gotcha: have to click the confirm link in the email or nothing gets sent
  endpoint  = var.alarm_email
}

# anything in the DLQ = a job failed all 3 tries. should basically never happen
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

# oldest job waiting > 10 min -> workers are dead or can't keep up
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
  threshold           = 600 # sec
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

# api 5xx, 5+ in 5 min. (1 random error isn't worth an email)
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
  treat_missing_data  = "notBreaching" # no traffic = no datapoints, that's fine not an alarm
  alarm_actions       = [aws_sns_topic.alarms.arn]
}
