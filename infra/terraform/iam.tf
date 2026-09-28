# IAM. least privilege - each container only gets what its code actually calls:
#   gateway-api:    presign S3 up/downloads, HEAD an upload, send to SQS
#   gateway-worker: get/put S3 objects, receive/delete/change visibility on SQS
#   cpp-core, ml, audio-producer, migrate: nothing, they never touch AWS
# db access isn't IAM at all, it's security groups + the password

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# learned: 2 kinds of role.
#   execution role = ECS itself uses it BEFORE the container starts (pull image, logs, fetch secrets)
#   task role = what my code gets at runtime
# they're easy to mix up, e.g. the DB secret goes on the EXECUTION role bc ECS injects it
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

# task roles (my code)
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
        # presigned url = signed w/ the API's creds, so the API needs the permission itself
        # even though it's the browser doing the actual PUT/GET
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject"]
        Resource = "${aws_s3_bucket.media.arn}/*"
      },
      {
        # gotcha: w/o ListBucket, HEAD on a missing key gives 403 not 404,
        # so "not uploaded yet" looks like a permissions error
        Effect    = "Allow"
        Action    = "s3:ListBucket"
        Resource  = aws_s3_bucket.media.arn
        Condition = { StringLike = { "s3:prefix" = "images/*" } }
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
        Effect = "Allow"
        # ChangeMessageVisibility = heartbeat + retry delay
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:ChangeMessageVisibility"]
        Resource = aws_sqs_queue.jobs.arn
      },
    ]
  })
}

# deploy.yml signs in w/ github's OIDC token -> no long lived AWS keys in github secrets.
# the sub condition below = only jobs in this repo's "production" environment
# (which needs my approval) can assume it
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

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

# admin bc it runs terraform apply, which manages everything incl. IAM itself.
# the trust policy above is the actual guard here, not this.
# TODO(maybe): scope this down, it's the broadest thing in the whole repo
resource "aws_iam_role_policy_attachment" "deploy" {
  role       = aws_iam_role.deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
