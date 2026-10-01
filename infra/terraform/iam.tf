# Least-privilege roles: execution (pull images, inject the DB secret), API (S3 + SQS send + RDS),
# worker (S3 + SQS receive + RDS), and the GitHub OIDC deploy role.
# ecs.tf attaches the api and worker roles; cpp-core, ml and audio-producer get no role at all.

# ---- Roles for ECS tasks ----

# Trust policy shared by the task roles: only ECS tasks may assume them.
data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# ECS uses the execution role before the container starts, so the DB secret it injects is granted here.
resource "aws_iam_role" "execution" {
  name               = "${var.app_name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

# AWS's managed policy for pulling from ECR and writing to CloudWatch Logs.
resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Read the one secret that holds the RDS password (app_secrets in ecs.tf).
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

# The api task's role. The code that uses each permission is in api/src/aws/.
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
        # Presigned upload and download links are signed with these (createUploadForm and
        # signDownloadUrl in s3.ts), so the link can only do what this role can do.
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject"]
        Resource = "${aws_s3_bucket.media.arn}/*"
      },
      {
        # Without ListBucket, HEAD on a missing key returns 403 instead of 404.
        # objectExists in s3.ts relies on getting NotFound.
        Effect    = "Allow"
        Action    = "s3:ListBucket"
        Resource  = aws_s3_bucket.media.arn
        Condition = { StringLike = { "s3:prefix" = "images/*" } }
      },
      {
        # enqueueJob in queue.ts. The api only sends; it never reads the queue.
        Effect   = "Allow"
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.jobs.arn
      },
    ]
  })
}

# The worker task's role.
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
        # getObject reads the uploaded image and putObject saves the WAV (s3.ts, from pipeline.ts).
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.media.arn}/*"
      },
      {
        # receiveJob, deleteJob, releaseJob and extendVisibility in queue.ts.
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:ChangeMessageVisibility"]
        Resource = aws_sqs_queue.jobs.arn
      },
    ]
  })
}

# ---- Deploy role for GitHub Actions ----

# Lets GitHub Actions prove who it is with a short-lived token, so no AWS keys are stored in GitHub.
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

# Only the production environment of this one repository can assume the role
# (.github/workflows/deploy.yml, which sets `environment: production`).
resource "aws_iam_role" "deploy" {
  name = "${var.app_name}-deploy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:production"
        }
      }
    }]
  })
}

# Broad because terraform apply manages IAM too. The trust policy above limits who can assume it.
resource "aws_iam_role_policy_attachment" "deploy" {
  role       = aws_iam_role.deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
