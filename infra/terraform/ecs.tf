# Containers: an ECR repository per image, one ECS cluster, and a Fargate
# service per container. The gateway image runs twice, as the API and as the worker.
# The worker finds the internal services by name through Cloud Map
# (for example http://cpp-core.soundcanvas.local:8080).

locals {
  namespace = "${var.app_name}.local"

  # Settings shared by the gateway API and worker (see gateway/.env.example).
  gateway_env = [
    { name = "AWS_REGION", value = var.aws_region },
    { name = "S3_BUCKET", value = aws_s3_bucket.media.bucket },
    { name = "SQS_QUEUE_URL", value = aws_sqs_queue.jobs.url },
    { name = "DB_HOST", value = aws_db_instance.main.address },
    { name = "DB_USER", value = aws_db_instance.main.username },
    { name = "DB_NAME", value = aws_db_instance.main.db_name },
    { name = "CPP_CORE_URL", value = "http://cpp-core.${local.namespace}:8080" },
    { name = "ML_URL", value = "http://ml.${local.namespace}:5000" },
    { name = "AUDIO_PRODUCER_URL", value = "http://audio-producer.${local.namespace}:9001" },
  ]
  gateway_secrets = [
    { name = "DB_PASSWORD", valueFrom = "${aws_db_instance.main.master_user_secret[0].secret_arn}:password::" },
  ]

  # cpu is in 1/1024ths of a vCPU; memory is in MB. Sizes follow what each service does:
  # the gateway only waits on I/O, TensorFlow needs memory, and audio rendering is the heaviest step.
  services = {
    gateway-api = {
      repo = "gateway", port = 4000, cpu = 256, memory = 512, command = null
      env  = local.gateway_env, secrets = local.gateway_secrets, role = aws_iam_role.api.arn
    }
    gateway-worker = {
      repo = "gateway", port = null, cpu = 256, memory = 512, command = ["npm", "run", "worker"]
      env  = local.gateway_env, secrets = local.gateway_secrets, role = aws_iam_role.worker.arn
    }
    cpp-core = {
      repo = "cpp-core", port = 8080, cpu = 512, memory = 1024, command = null
      env  = [], secrets = [], role = null
    }
    ml = {
      repo = "ml", port = 5000, cpu = 512, memory = 2048, command = null
      env  = [], secrets = [], role = null
    }
    audio-producer = {
      repo = "audio-producer", port = 9001, cpu = 1024, memory = 2048, command = null
      env  = [], secrets = [], role = null
    }
  }

  # The services the worker calls by name.
  internal_services = toset(["cpp-core", "ml", "audio-producer"])
}

resource "aws_ecr_repository" "repo" {
  for_each = toset(["gateway", "cpp-core", "ml", "audio-producer"])
  name     = "${var.app_name}/${each.key}"
}

resource "aws_ecs_cluster" "main" {
  name = var.app_name
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

resource "aws_ecs_task_definition" "service" {
  for_each                 = local.services
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

resource "aws_ecs_service" "service" {
  for_each        = local.services
  name            = each.key
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.service[each.key].arn
  desired_count   = 1 # one task each; a single worker processes jobs one at a time, in FIFO order
  launch_type     = "FARGATE"

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

  depends_on = [aws_lb_listener.https]
}
