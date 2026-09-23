# Permissions. Each container gets only what its code uses:
#   gateway-api:    presign S3 uploads/downloads, send to the queue
#   gateway-worker: read/write S3 objects, receive and delete queue messages
#   cpp-core, ml, audio-producer: no AWS permissions (they only answer HTTP)
# Database access is controlled by the network (security groups) and the password, not IAM.

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# The execution role is used by ECS itself: pull images, write logs, read the DB password secret.
resource "aws_iam_role" "execution" {
  name               = "${var.app_name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_db_secret" {
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = aws_db_instance.main.master_user_secret[0].secret_arn
    }]
  })
}

# Task roles are used by our code.
resource "aws_iam_role" "api" {
  name               = "${var.app_name}-api"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "api" {
  role = aws_iam_role.api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # A presigned URL carries the signer's permissions, so the API needs the
        # same S3 actions the browser performs with it.
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject"]
        Resource = "${aws_s3_bucket.media.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.jobs.arn
      },
    ]
  })
}

resource "aws_iam_role" "worker" {
  name               = "${var.app_name}-worker"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "worker" {
  role = aws_iam_role.worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.media.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage"]
        Resource = aws_sqs_queue.jobs.arn
      },
    ]
  })
}
