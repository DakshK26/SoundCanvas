# Values needed after apply: the GraphQL URL for the frontend, the ECR repos, and the deploy role ARN.

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

output "deploy_role_arn" {
  description = "Set this as the AWS_DEPLOY_ROLE_ARN variable of the GitHub production environment."
  value       = aws_iam_role.deploy.arn
}

output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "private_subnet_ids" {
  value = join(",", aws_subnet.private[*].id)
}

output "tasks_security_group_id" {
  value = aws_security_group.tasks.id
}
