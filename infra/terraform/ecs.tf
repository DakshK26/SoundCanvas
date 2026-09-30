# The five ECS services, their images, autoscaling and the one-off migrate task.
# api sits behind the ALB; the others are reached by Cloud Map name.

locals {
  namespace = "${var.app_name}.local"

  app_env = [
    { name = "AWS_REGION", value = var.aws_region },
    { name = "S3_BUCKET", value = aws_s3_bucket.media.bucket },
    { name = "SQS_QUEUE_URL", value = aws_sqs_queue.jobs.url },
    { name = "DB_HOST", value = aws_db_instance.main.address },
    { name = "DB_USER", value = aws_db_instance.main.username },
    { name = "DB_NAME", value = aws_db_instance.main.db_name },
    { name = "FRONTEND_ORIGIN", value = var.frontend_origin },
    { name = "CPP_CORE_URL", value = "http://cpp-core.${local.namespace}:8080" },
    { name = "ML_URL", value = "http://ml.${local.namespace}:5000" },
    { name = "AUDIO_PRODUCER_URL", value = "http://audio-producer.${local.namespace}:9001" },
  ]
  app_secrets = [
    { name = "DB_PASSWORD", valueFrom = "${aws_db_instance.main.master_user_secret[0].secret_arn}:password::" },
  ]

  # The slim Python images have no curl.
  python_health = "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://localhost:%d/health').status != 200)"

  # cpu in 1/1024 vCPU, memory in MB
  services = {
    api = {
      repo   = "api", port = 4000, cpu = 256, memory = 512, command = null
      env    = local.app_env, secrets = local.app_secrets, role = aws_iam_role.api.arn
      health = null, stop_timeout = null
    }
    worker = {
      repo = "api", port = null, cpu = 256, memory = 512, command = ["npm", "run", "worker"]
      env  = local.app_env, secrets = local.app_secrets, role = aws_iam_role.worker.arn
      # 120 s is the Fargate maximum, enough for the worker to finish its current song.
      health = null, stop_timeout = 120
    }
    cpp-core = {
      repo   = "cpp-core", port = 8080, cpu = 512, memory = 1024, command = null
      env    = [], secrets = [], role = null
      health = ["CMD", "curl", "-f", "http://localhost:8080/health"], stop_timeout = null
    }
    ml = {
      repo   = "ml", port = 5000, cpu = 512, memory = 2048, command = null
      env    = [], secrets = [], role = null
      health = ["CMD", "python", "-c", format(local.python_health, 5000)], stop_timeout = null
    }
    audio-producer = {
      repo   = "audio-producer", port = 9001, cpu = 1024, memory = 2048, command = null
      env    = [], secrets = [], role = null
      health = ["CMD", "python", "-c", format(local.python_health, 9001)], stop_timeout = null
    }
  }

  tasks = merge(local.services, {
    migrate = {
      repo   = "api", port = null, cpu = 256, memory = 512, command = ["npm", "run", "migrate"]
      env    = local.app_env, secrets = local.app_secrets, role = null
      health = null, stop_timeout = null
    }
  })

  internal_services = toset(["cpp-core", "ml", "audio-producer"])
}

resource "aws_ecr_repository" "repo" {
  for_each             = toset(["api", "cpp-core", "ml", "audio-producer"])
  name                 = "${var.app_name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "repo" {
  for_each   = aws_ecr_repository.repo
  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 20 most recent images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 20 }
      action       = { type = "expire" }
    }]
  })
}

resource "aws_ecs_cluster" "main" {
  name = var.app_name

  setting {
    name  = "containerInsights" # the worker scaling policy needs its RunningTaskCount metric
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.app_name}"
  retention_in_days = 14
}

resource "aws_service_discovery_private_dns_namespace" "main" {
  name = local.namespace
  vpc  = aws_vpc.main.id
}

resource "aws_service_discovery_service" "internal" {
  for_each = local.internal_services
  name     = each.key

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id
    dns_records {
      type = "A"
      ttl  = 10 # seconds
    }
  }
}

resource "aws_ecs_task_definition" "task" {
  for_each                 = local.tasks
  family                   = "${var.app_name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = each.value.role

  container_definitions = jsonencode([{
    name         = each.key
    image        = "${aws_ecr_repository.repo[each.value.repo].repository_url}:${var.image_tag}"
    command      = each.value.command
    essential    = true
    portMappings = each.value.port == null ? [] : [{ containerPort = each.value.port }]
    environment  = each.value.env
    secrets      = each.value.secrets
    stopTimeout  = each.value.stop_timeout
    healthCheck = each.value.health == null ? null : {
      command     = each.value.health
      interval    = 30 # seconds
      retries     = 3
      startPeriod = 60 # ml takes a while to import TensorFlow
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.ecs.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = each.key
      }
    }
  }])
}

moved {
  from = aws_ecs_task_definition.service
  to   = aws_ecs_task_definition.task
}

resource "aws_ecs_service" "service" {
  for_each        = local.services
  name            = each.key
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.task[each.key].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  # Without this, apply passes even when the new tasks crash loop.
  wait_for_steady_state = true

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.tasks.id]
  }

  dynamic "load_balancer" {
    for_each = each.key == "api" ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.api.arn
      container_name   = each.key
      container_port   = each.value.port
    }
  }

  dynamic "service_registries" {
    for_each = contains(local.internal_services, each.key) ? [1] : []
    content {
      registry_arn = aws_service_discovery_service.internal[each.key].arn
    }
  }

  lifecycle {
    ignore_changes = [desired_count] # otherwise every apply resets it to 1 and fights autoscaling
  }

  depends_on = [aws_lb_listener.https]
}

resource "aws_appautoscaling_target" "service" {
  for_each           = setunion(local.internal_services, ["worker"])
  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.service[each.key].name}"
  min_capacity       = 1
  max_capacity       = 5
}

resource "aws_appautoscaling_policy" "worker_backlog" {
  name               = "${var.app_name}-worker-backlog"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.service["worker"].service_namespace
  scalable_dimension = aws_appautoscaling_target.service["worker"].scalable_dimension
  resource_id        = aws_appautoscaling_target.service["worker"].resource_id

  target_tracking_scaling_policy_configuration {
    target_value = 2
    customized_metric_specification {
      metrics {
        id          = "waiting"
        return_data = false
        metric_stat {
          stat = "Sum"
          metric {
            namespace   = "AWS/SQS"
            metric_name = "ApproximateNumberOfMessagesVisible"
            dimensions {
              name  = "QueueName"
              value = aws_sqs_queue.jobs.name
            }
          }
        }
      }
      metrics {
        id          = "workers"
        return_data = false
        metric_stat {
          stat = "Average"
          metric {
            namespace   = "ECS/ContainerInsights"
            metric_name = "RunningTaskCount"
            dimensions {
              name  = "ClusterName"
              value = aws_ecs_cluster.main.name
            }
            dimensions {
              name  = "ServiceName"
              value = aws_ecs_service.service["worker"].name
            }
          }
        }
      }
      metrics {
        id          = "backlog_per_worker"
        label       = "Waiting jobs per running worker"
        expression  = "waiting / workers"
        return_data = true
      }
    }
  }
}

resource "aws_appautoscaling_policy" "service_cpu" {
  for_each           = local.internal_services
  name               = "${var.app_name}-${each.key}-cpu"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.service[each.key].service_namespace
  scalable_dimension = aws_appautoscaling_target.service[each.key].scalable_dimension
  resource_id        = aws_appautoscaling_target.service[each.key].resource_id

  target_tracking_scaling_policy_configuration {
    target_value = 60 # percent CPU
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
