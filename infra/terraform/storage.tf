# Storage: S3 for the files (uploaded images, generated WAVs) and RDS MySQL
# for the `generations` table that tracks each job's status.

resource "aws_s3_bucket" "media" {
  bucket = var.bucket_name
}

# Nothing in the bucket is public; the browser only uses short-lived presigned URLs.
resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lets the frontend POST images (presigned upload form) and GET songs straight from the browser.
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  cors_rule {
    allowed_origins = [var.frontend_origin]
    allowed_methods = ["POST", "GET"]
    allowed_headers = ["*"]
    max_age_seconds = 3600
  }
}

# Uploads and songs are deleted after 30 days; the history list hides older jobs
# to match (FILE_RETENTION_DAYS in gateway/src/db.ts).
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  dynamic "rule" {
    for_each = ["images/", "audio/"]
    content {
      id     = "expire-${trimsuffix(rule.value, "/")}"
      status = "Enabled"
      filter {
        prefix = rule.value
      }
      expiration {
        days = 30
      }
    }
  }
}

resource "aws_db_subnet_group" "main" {
  name       = var.app_name
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier        = "${var.app_name}-prototype"
  engine            = "mysql"
  engine_version    = "8.0"
  instance_class    = "db.t4g.micro" # smallest current-generation size; plenty for one table
  allocated_storage = 20             # GB, the MySQL minimum
  storage_encrypted = true
  # Single-AZ: a failure means minutes of downtime while RDS recovers, which a
  # prototype accepts. multi_az = true adds a standby for about twice the cost.

  db_name  = var.app_name
  username = var.app_name
  # RDS generates the password and keeps it in Secrets Manager; ECS injects it into the gateway.
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  backup_retention_period  = 7 # days of daily snapshots, restorable to any point in time
  delete_automated_backups = false
  deletion_protection      = var.deletion_protection
  skip_final_snapshot      = true # the automated backups above outlive the instance for 7 days
}
