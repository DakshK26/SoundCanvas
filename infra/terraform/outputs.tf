# Values needed after apply: the GraphQL URL for the frontend, the ECR repos, and the deploy role ARN.
# `terraform output <name>` prints one. deploy.yml reads the last few to run the migrate task.

output "api_url" {
  description = "Set this as NEXT_PUBLIC_GRAPHQL_ENDPOINT in the frontend (after pointing a DNS name at it that matches the certificate)."
  value       = "https://${aws_lb.api.dns_name}/graphql"
}

# A map from service name to repository URL, e.g. { api = "....amazonaws.com/soundcanvas/api", ... }.
output "ecr_repositories" {
  description = "Push each service's image here."
  value       = { for name, repo in aws_ecr_repository.repo : name => repo.repository_url }
}

# Handy for checking a local or LocalStack setup against the real names.
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

# The migrate task is started with `aws ecs run-task` in deploy.yml, which needs the cluster,
# the private subnets (comma separated) and the tasks security group.
output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "private_subnet_ids" {
  value = join(",", aws_subnet.private[*].id)
}

output "tasks_security_group_id" {
  value = aws_security_group.tasks.id
}
