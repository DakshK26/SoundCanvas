# Values printed after `terraform apply`.

output "api_url" {
  description = "Set this as NEXT_PUBLIC_GRAPHQL_ENDPOINT in the frontend (after pointing a DNS name at it that matches the certificate)."
  value       = "https://${aws_lb.api.dns_name}/graphql"
}

output "ecr_repositories" {
  description = "Push each service's image here."
  value       = { for name, repo in aws_ecr_repository.repo : name => repo.repository_url }
}

output "bucket_name" {
  value = aws_s3_bucket.media.bucket
}

output "queue_url" {
  value = aws_sqs_queue.jobs.url
}

output "database_endpoint" {
  value = aws_db_instance.main.address
}
