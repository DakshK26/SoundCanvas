# Containers: an ECR repository per image, one ECS cluster, and a Fargate
# service per container. The gateway image runs three ways: as the API, as the
# worker, and as a one-off migration task that the deploy workflow runs first.
# The worker finds the internal services by name through Cloud Map
# (for example http://cpp-core.soundcanvas.local:8080).

locals {
  namespace = "${var.app_name}.local"

  # Settings shared by the gateway API, worker and migration (see gateway/.env.example).
  gateway_env = [
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
  gateway_secrets = [
    { name = "DB_PASSWORD", valueFrom = "${aws_db_instance.main.master_user_secret[0].secret_arn}:password::" },
  ]

  # A container health check: ECS replaces a task whose /health stops answering.
  # (The API is checked by the load balancer instead; the worker has no port.)
  python_health = "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://localhost:%d/health').status != 200)"

  # cpu is in 1/1024ths of a vCPU; memory is in MB. Sizes follow what each service does:
  # the gateway only waits on I/O, TensorFlow needs memory, and audio rendering is the heaviest step.
  services = {
    gateway-api = {
      repo   = "gateway", port = 4000, cpu = 256, memory = 512, command = null
      env    = local.gateway_env, secrets = local.gateway_secrets, role = aws_iam_role.api.arn
      health = null, stop_timeout = null
    }
    gateway-worker = {
      repo = "gateway", port = null, cpu = 256, memory = 512, command = ["npm", "run", "worker"]
      env  = local.gateway_env, secrets = local.gateway_secrets, role = aws_iam_role.worker.arn
      # On a deploy or scale-in, ECS sends SIGTERM and waits this long (the Fargate maximum)
      # before killing the task, so the worker can finish the song it is making.
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

  # Every task definition: the long-running services plus the migration, which has no service.
  tasks = merge(local.services, {
    migrate = {
      repo   = "gateway", port = null, cpu = 256, memory = 512, command = ["npm", "run", "migrate"]
      env    = local.gateway_env, secrets = local.gateway_secrets, role = null
      health = null, stop_timeout = null
    }
  })

  # The services the worker calls by name.
  internal_services = toset(["cpp-core", "ml", "audio-producer"])
}

# Tags are immutable, so an image tag (the git SHA) always means the same code.
resource "aws_ecr_repository" "repo" {
  for_each             = toset(["gateway", "cpp-core", "ml", "audio-producer"])
  name                 = "${var.app_name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true # checks each pushed image for known vulnerabilities
  }
}

# Every deploy pushes new images; keep the last 20 of each so old ones can be rolled back to.
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
    name  = "containerInsights" # per-service CPU, memory and task-count metrics
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
      ttl  = 10 # seconds; short so a replaced task is found quickly
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
      interval    = 30 # seconds between checks
      retries     = 3
      startPeriod = 60 # ml loads TensorFlow before it answers
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

moved { # renamed when the migration task was added
  from = aws_ecs_task_definition.service
  to   = aws_ecs_task_definition.task
}

resource "aws_ecs_service" "service" {
  for_each        = local.services
  name            = each.key
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.task[each.key].arn
  desired_count   = 1 # the starting count; auto scaling below adjusts it
  launch_type     = "FARGATE"

  # A deploy whose new tasks keep failing is stopped and rolled back to the last working version,
  # and `terraform apply` waits for that outcome, so the deploy workflow fails instead of reporting success.
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  wait_for_steady_state = true

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.tasks.id]
  }

  # Only the API sits behind the load balancer.
  dynamic "load_balancer" {
    for_each = each.key == "gateway-api" ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.api.arn
      container_name   = each.key
      container_port   = each.value.port
    }
  }

  # Internal services register their address in Cloud Map.
  dynamic "service_registries" {
    for_each = contains(local.internal_services, each.key) ? [1] : []
    content {
      registry_arn = aws_service_discovery_service.internal[each.key].arn
    }
  }

  lifecycle {
    ignore_changes = [desired_count] # owned by auto scaling after the first deploy
  }

  depends_on = [aws_lb_listener.https]
}

# Auto scaling: each service below runs between 1 and 5 tasks.
resource "aws_appautoscaling_target" "service" {
  for_each           = setunion(local.internal_services, ["gateway-worker"])
  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.service[each.key].name}"
  min_capacity       = 1
  max_capacity       = 5
}

# Workers scale on backlog per worker: waiting jobs divided by running workers,
# aiming for 2. A song takes about a minute, so that keeps the wait near two minutes.
# Jobs from one browser share a message group and still run one at a time;
# extra workers help when many browsers are waiting.
resource "aws_appautoscaling_policy" "worker_backlog" {
  name               = "${var.app_name}-worker-backlog"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.service["gateway-worker"].service_namespace
  scalable_dimension = aws_appautoscaling_target.service["gateway-worker"].scalable_dimension
  resource_id        = aws_appautoscaling_target.service["gateway-worker"].resource_id

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
              value = aws_ecs_service.service["gateway-worker"].name
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

# The internal services scale on CPU, so more workers don't overload them.
resource "aws_appautoscaling_policy" "service_cpu" {
  for_each           = local.internal_services
  name               = "${var.app_name}-${each.key}-cpu"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.service[each.key].service_namespace
  scalable_dimension = aws_appautoscaling_target.service[each.key].scalable_dimension
  resource_id        = aws_appautoscaling_target.service[each.key].resource_id

  target_tracking_scaling_policy_configuration {
    target_value = 60 # percent average CPU; leaves headroom while new tasks start
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
