# The S3 bucket for images and WAVs (CORS, 30-day lifecycle) and the RDS MySQL instance.
# The api and worker reach both through api/src/aws/s3.ts and api/src/db.ts.

# ---- S3 ----

# Keys are images/{id} (uploaded by the browser) and audio/{id}.wav (written by the worker).
resource "aws_s3_bucket" "media" {
  bucket = var.bucket_name
}

# Nothing in the bucket can ever be made public. Browsers only get presigned links.
resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true # Block access control lists
  block_public_policy     = true
  ignore_public_acls      = true 
  restrict_public_buckets = true 
}

# The browser posts the upload form and fetches the WAV straight from S3, so S3 has to allow
# requests from the frontend's origin (Playground.tsx uploads, AudioPlayer.tsx downloads).
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  cors_rule {
    allowed_origins = [var.frontend_origin]
    allowed_methods = ["POST", "GET"]
    allowed_headers = ["*"]
    max_age_seconds = 3600
  }
}

# Delete images and songs after 30 days. One rule per prefix, written by the dynamic block.
# Must match FILE_RETENTION_DAYS in db.ts.
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

# ---- MySQL ----

# RDS has to be given at least two subnets in different zones, even for a single instance.
resource "aws_db_subnet_group" "main" {
  name       = var.app_name
  subnet_ids = aws_subnet.private[*].id
}

# One small MySQL 8 instance holding the generations table (api/migrations/001_create_generations.sql).
resource "aws_db_instance" "main" {
  identifier        = "${var.app_name}-prototype"
  engine            = "mysql"
  engine_version    = "8.0"
  instance_class    = "db.t4g.micro"
  allocated_storage = 20 # GB, the MySQL minimum
  storage_encrypted = true

  db_name  = var.app_name
  username = var.app_name
  # RDS keeps the password in Secrets Manager, so it never appears in Terraform state.
  manage_master_user_password = true

  # Private subnets and the db security group from network.tf; no public address.
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  backup_retention_period  = 7 # days
  delete_automated_backups = false
  deletion_protection      = var.deletion_protection
  skip_final_snapshot      = true
}
