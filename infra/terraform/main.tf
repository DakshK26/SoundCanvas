# SoundCanvas AWS Infrastructure
# NO CREDENTIALS IN THIS FILE - Configure via terraform.tfvars (gitignored)

terraform {
  required_version = ">= 1.0"
  
  backend "s3" {
    bucket = "soundcanvas-terraform-state-dk"
    key    = "terraform.tfstate"
    region = "us-east-2"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  default = "us-east-2"
}

variable "environment" {
  default = "prod"
}

variable "app_name" {
  default = "soundcanvas"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "ecr_gateway_uri" {
  type = string
}

variable "ecr_cpp_core_uri" {
  type = string
}

variable "ecr_audio_producer_uri" {
  type = string
}

# Data source - get existing RDS instance
data "aws_db_instance" "main" {
  db_instance_identifier = "soundcanvas-db"
}

# Data source - get existing S3 bucket
data "aws_s3_bucket" "uploads" {
  bucket = "soundcanvas-uploads-dk"
}

# Data source - get existing default VPC (where RDS is)
data "aws_vpc" "main" {
  default = true
}

# Data source - get existing public subnets
data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  filter {
    name   = "map-public-ip-on-launch"
    values = ["true"]
  }
}

# Security Group - ALB
resource "aws_security_group" "alb" {
  name        = "${var.app_name}-alb-sg"
  description = "ALB security group"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-alb-sg"
  }
}

# Security Group - ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.app_name}-ecs-tasks-sg"
  description = "ECS tasks security group"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    from_port       = 4000
    to_port         = 4000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port       = 5000
    to_port         = 5000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.app_name}-ecs-tasks-sg"
  }
}

# Security Group Rule - Allow ECS tasks to access RDS
resource "aws_security_group_rule" "rds_from_ecs" {
  type                     = "ingress"
  from_port                = 3306
  to_port                  = 3306
  protocol                 = "tcp"
  security_group_id        = "sg-0acd7b3ad5ab7271a"  # RDS security group
  source_security_group_id = aws_security_group.ecs_tasks.id
  description              = "Allow ECS tasks to access RDS"
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.app_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.public.ids

  tags = {
    Name = "${var.app_name}-alb"
  }
}

# Target Groups
resource "aws_lb_target_group" "gateway" {
  name        = "${var.app_name}-gateway-tg"
  port        = 4000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/graphql"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 60
    interval            = 120
    matcher             = "200,400"
  }
}

resource "aws_lb_target_group" "cpp_core" {
  name        = "${var.app_name}-cpp-core-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 60
    interval            = 120
  }
}

resource "aws_lb_target_group" "audio_producer" {
  name        = "${var.app_name}-audio-tg"
  port        = 5000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 60
    interval            = 120
  }
}

# ALB Listeners
resource "aws_lb_listener" "main" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.gateway.arn
  }
}

# Listener rules for cpp-core service
resource "aws_lb_listener_rule" "cpp_core" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.cpp_core.arn
  }

  condition {
    path_pattern {
      values = ["/compose*"]
    }
  }
}

# Listener rules for audio-producer service
resource "aws_lb_listener_rule" "audio_producer" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.audio_producer.arn
  }

  condition {
    path_pattern {
      values = ["/render*"]
    }
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/ecs/${var.app_name}/gateway"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "cpp_core" {
  name              = "/ecs/${var.app_name}/cpp-core"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "audio_producer" {
  name              = "/ecs/${var.app_name}/audio-producer"
  retention_in_days = 7
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.app_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Tasks (application permissions)
resource "aws_iam_role" "ecs_task" {
  name = "${var.app_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

# S3 access policy for tasks
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${var.app_name}-ecs-task-s3-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${data.aws_s3_bucket.uploads.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = data.aws_s3_bucket.uploads.arn
      }
    ]
  })
}

# ECS Task Definition - Gateway
resource "aws_ecs_task_definition" "gateway" {
  family                   = "${var.app_name}-gateway"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "gateway"
    image = "${var.ecr_gateway_uri}:latest"
    portMappings = [{
      containerPort = 4000
      protocol      = "tcp"
    }]
    environment = [
      { name = "PORT", value = "4000" },
      { name = "NODE_ENV", value = "production" },
      { name = "DB_HOST", value = data.aws_db_instance.main.address },
      { name = "DB_PORT", value = tostring(data.aws_db_instance.main.port) },
      { name = "DB_NAME", value = "soundcanvas" },
      { name = "DB_USER", value = "admin" },
      { name = "DB_PASSWORD", value = var.db_password },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "S3_BUCKET_NAME", value = data.aws_s3_bucket.uploads.id },
      { name = "CPP_CORE_URL", value = "http://localhost:8080" },
      { name = "AUDIO_PRODUCER_URL", value = "http://localhost:5000" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.gateway.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# ECS Task Definition - CPP Core
resource "aws_ecs_task_definition" "cpp_core" {
  family                   = "${var.app_name}-cpp-core"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "cpp-core"
    image = "${var.ecr_cpp_core_uri}:latest"
    portMappings = [{
      containerPort = 8080
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.cpp_core.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# ECS Task Definition - Audio Producer
resource "aws_ecs_task_definition" "audio_producer" {
  family                   = "${var.app_name}-audio-producer"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "audio-producer"
    image = "${var.ecr_audio_producer_uri}:latest"
    portMappings = [{
      containerPort = 5000
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.audio_producer.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# ECS Services
resource "aws_ecs_service" "gateway" {
  name            = "${var.app_name}-gateway-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.gateway.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.public.ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.gateway.arn
    container_name   = "gateway"
    container_port   = 4000
  }

  depends_on = [aws_lb_listener.main]
}

resource "aws_ecs_service" "cpp_core" {
  name            = "${var.app_name}-cpp-core-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.cpp_core.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.public.ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.cpp_core.arn
    container_name   = "cpp-core"
    container_port   = 8080
  }

  depends_on = [aws_lb_listener.main]
}

resource "aws_ecs_service" "audio_producer" {
  name            = "${var.app_name}-audio-producer-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.audio_producer.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.public.ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.audio_producer.arn
    container_name   = "audio-producer"
    container_port   = 5000
  }

  depends_on = [aws_lb_listener.main]
}

# Outputs
output "alb_dns_name" {
  description = "Application Load Balancer DNS name - use this as your API endpoint"
  value       = aws_lb.main.dns_name
}

output "graphql_endpoint" {
  description = "GraphQL API endpoint"
  value       = "http://${aws_lb.main.dns_name}/graphql"
}

output "rds_endpoint" {
  description = "RDS Database endpoint"
  value       = data.aws_db_instance.main.address
}

output "s3_bucket" {
  description = "S3 uploads bucket"
  value       = data.aws_s3_bucket.uploads.id
}
