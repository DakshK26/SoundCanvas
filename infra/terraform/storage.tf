# storage. S3 = files (images, wavs), RDS MySQL = the generations table (job status etc)

resource "aws_s3_bucket" "media" {
  bucket = var.bucket_name
}

# bucket is fully private. browser only ever gets 15 min presigned urls
resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS so the browser can POST the upload form + GET the wav directly (fetch() needs this, <img> doesn't)
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  cors_rule {
    allowed_origins = [var.frontend_origin]
    allowed_methods = ["POST", "GET"]
    allowed_headers = ["*"]
    max_age_seconds = 3600
  }
}

# delete files after 30 days. history hides jobs older than that too so there's no
# broken links (FILE_RETENTION_DAYS in db.ts - keep them the same)
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
  instance_class    = "db.t4g.micro" # smallest current gen, way more than 1 table needs
  allocated_storage = 20             # GB, mysql minimum
  storage_encrypted = true
  # single AZ. if it fails it's a few min down while RDS recovers - ok for a prototype.
  # multi_az = true gives a standby but ~2x the price

  db_name  = var.app_name
  username = var.app_name
  # RDS makes the password + stores it in Secrets Manager, ECS injects it as DB_PASSWORD.
  # -> the password is never in terraform vars or state
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  backup_retention_period  = 7 # days. also turns on point-in-time restore
  delete_automated_backups = false
  deletion_protection      = var.deletion_protection
  skip_final_snapshot      = true # ok bc delete_automated_backups = false keeps the backups for 7 days anyway
}
