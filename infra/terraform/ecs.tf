# The five ECS services, their images, autoscaling and the one-off migrate task.
# api sits behind the ALB (network.tf); the others are reached by Cloud Map name.
# IAM roles come from iam.tf, the queue from queue.tf, the bucket and database from storage.tf.

# ---- Shared settings ----

locals {
  # Private DNS zone, so the worker can call http://cpp-core.soundcanvas.local:8080.
  namespace = "${var.app_name}.local"

  # Environment for the api, worker and migrate containers. api/src/env.ts reads each of these
  # with requireEnv, and the last three are the base URLs in api/src/serviceClients.ts.
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
  # The database password is never in Terraform state as text. RDS keeps it in Secrets Manager,
  # and ECS reads the "password" key from that secret when the container starts.
  app_secrets = [
    { name = "DB_PASSWORD", valueFrom = "${aws_db_instance.main.master_user_secret[0].secret_arn}:password::" },
  ]

  # Health check for the Python services. The slim Python images have no curl, so this asks
  # /health with urllib and exits non-zero unless it gets a 200. %d is filled with the port.
  python_health = "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://localhost:%d/health').status != 200)"

  # One entry per long-running service. Every resource below loops over this map.
  # repo is the ECR repository (api and worker share one image), cpu is in 1/1024 vCPU,
  # memory in MB, command overrides the image's CMD, role is the task's own IAM role.
  services = {
    api = {
      repo   = "api", port = 4000, cpu = 256, memory = 512, command = null
      env    = local.app_env, secrets = local.app_secrets, role = aws_iam_role.api.arn
      health = null, stop_timeout = null
    }
    worker = {
      repo = "api", port = null, cpu = 256, memory = 512, command = ["npm", "run", "worker"]
      env  = local.app_env, secrets = local.app_secrets, role = aws_iam_role.worker.arn
      # 120 s is the Fargate maximum, enough for the worker to finish its current song after the
      # SIGTERM handler in api/src/worker.ts stops it taking new jobs.
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

  # Task definitions are the services plus migrate. migrate has a task definition but no service:
  # .github/workflows/deploy.yml runs it once per deploy (api/src/migrate.ts).
  tasks = merge(local.services, {
    migrate = {
      repo   = "api", port = null, cpu = 256, memory = 512, command = ["npm", "run", "migrate"]
      env    = local.app_env, secrets = local.app_secrets, role = null
      health = null, stop_timeout = null
    }
  })

  # The three stateless HTTP services: registered in Cloud Map and scaled on CPU.
  internal_services = toset(["cpp-core", "ml", "audio-producer"])
}

# ---- Container images ----

# One ECR repository per image. Tags are immutable, so a git SHA tag always means the same image.
resource "aws_ecr_repository" "repo" {
  for_each             = toset(["api", "cpp-core", "ml", "audio-producer"])
  name                 = "${var.app_name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Every deploy pushes new images, so old ones are deleted after the 20 most recent.
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

# ---- Cluster, logs and service discovery ----

resource "aws_ecs_cluster" "main" {
  name = var.app_name

  setting {
    name  = "containerInsights" # the worker scaling policy needs its RunningTaskCount metric
    value = "enabled"
  }
}

# Every container's stdout goes here. api/src/log.ts writes one JSON line per event.
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.app_name}"
  retention_in_days = 14
}

# Cloud Map: a private DNS zone inside the VPC.
resource "aws_service_discovery_private_dns_namespace" "main" {
  name = local.namespace
  vpc  = aws_vpc.main.id
}

# One DNS name per internal service. Each running task adds its private IP as an A record,
# and the short TTL means new or replaced tasks are found within seconds.
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

# ---- Task definitions: what each container runs ----

resource "aws_ecs_task_definition" "task" {
  for_each                 = local.tasks
  family                   = "${var.app_name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc" # each task gets its own private IP in the VPC
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.execution.arn # used by ECS itself to pull the image and read the secret
  task_role_arn            = each.value.role            # used by the code inside the container

  container_definitions = jsonencode([{
    name  = each.key
    image = "${aws_ecr_repository.repo[each.value.repo].repository_url}:${var.image_tag}"
    # null keeps the Dockerfile's CMD (npm run api for the api image).
    command   = each.value.command
    essential = true
    # Only containers that listen on a port get a port mapping (not the worker or migrate).
    portMappings = each.value.port == null ? [] : [{ containerPort = each.value.port }]
    environment  = each.value.env
    secrets      = each.value.secrets
    stopTimeout  = each.value.stop_timeout
    # ECS runs this command inside the container and replaces the task after 3 failures.
    # The api has no health command here; the load balancer checks its /health instead.
    healthCheck = each.value.health == null ? null : {
      command     = each.value.health
      interval    = 30 # seconds
      retries     = 3
      startPeriod = 60 # ml takes a while to import TensorFlow
    }
    # Send stdout to the log group above, one stream per container.
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

# This resource used to be called "service". The moved block tells Terraform it is the same
# resource under a new name, so it is not deleted and recreated.
moved {
  from = aws_ecs_task_definition.service
  to   = aws_ecs_task_definition.task
}

# ---- Services: keep the tasks running ----

resource "aws_ecs_service" "service" {
  for_each        = local.services
  name            = each.key
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.task[each.key].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  # If a new deploy's tasks never become healthy, ECS goes back to the previous task definition.
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  # Without this, apply passes even when the new tasks crash loop.
  wait_for_steady_state = true

  # Private subnets only. The tasks security group is in network.tf.
  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.tasks.id]
  }

  # A dynamic block is written once per item in for_each. [1] means once and [] means not at all,
  # so only the api service is attached to the load balancer's target group.
  dynamic "load_balancer" {
    for_each = each.key == "api" ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.api.arn
      container_name   = each.key
      container_port   = each.value.port
    }
  }

  # The same trick: only the three internal services register a Cloud Map DNS name.
  dynamic "service_registries" {
    for_each = contains(local.internal_services, each.key) ? [1] : []
    content {
      registry_arn = aws_service_discovery_service.internal[each.key].arn
    }
  }

  lifecycle {
    ignore_changes = [desired_count] # otherwise every apply resets it to 1 and fights autoscaling
  }

  # The target group has to be attached to a listener before a service can register with it.
  depends_on = [aws_lb_listener.https]
}

# ---- Autoscaling ----

# Which services may scale, and between how many tasks. The api stays at one task.
resource "aws_appautoscaling_target" "service" {
  for_each           = setunion(local.internal_services, ["worker"])
  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.service[each.key].name}"
  min_capacity       = 1
  max_capacity       = 5
}

# Workers scale on queue backlog, not CPU, because they spend most of their time waiting on the
# other services. Target tracking adds or removes workers to keep about 2 waiting jobs per worker.
resource "aws_appautoscaling_policy" "worker_backlog" {
  name               = "${var.app_name}-worker-backlog"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.service["worker"].service_namespace
  scalable_dimension = aws_appautoscaling_target.service["worker"].scalable_dimension
  resource_id        = aws_appautoscaling_target.service["worker"].resource_id

  target_tracking_scaling_policy_configuration {
    target_value = 2
    # A metric maths expression: two raw metrics (return_data = false) and the ratio between them,
    # which is the one the policy tracks.
    customized_metric_specification {
      # Messages waiting in the SQS queue from queue.tf.
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
      # Worker tasks running right now (from Container Insights on the cluster).
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

# cpp-core, ml and audio-producer do real work per request, so average CPU is the right signal.
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
