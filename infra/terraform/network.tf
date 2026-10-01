# VPC, two public and two private subnets, one NAT, the ALB and the security groups.
# The Cloud Map DNS zone the tasks use to find each other is in ecs.tf.
# Only the ALB is public; every container (ecs.tf) and the database (storage.tf) sit on a private subnet.

# ---- Address space ----

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2) # the ALB and RDS subnet group need at least 2
}

# 10.0.0.0/16 gives 65,536 private addresses to split into subnets.
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true # needed for the Cloud Map names to resolve
  tags                 = { Name = var.app_name }
}

# cidrsubnet(..., 8, n) cuts a /24 out of the /16: public subnets are 10.0.0.0/24 and 10.0.1.0/24.
# Only the load balancer and the NAT live here.
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  availability_zone       = local.azs[count.index]
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.app_name}-public-${count.index}" }
}

# Private subnets are 10.0.10.0/24 and 10.0.11.0/24. The ECS tasks and RDS live here.
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  availability_zone = local.azs[count.index]
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 10)
  tags              = { Name = "${var.app_name}-private-${count.index}" }
}

# ---- Routing ----

# The internet gateway is the VPC's door to the internet, for the public subnets.
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

# Public subnets send all outside traffic (0.0.0.0/0) straight to the internet gateway.
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# The NAT lets private tasks open connections out (to ECR, SQS, Secrets Manager) without being
# reachable from outside. It needs a fixed public IP and sits in the first public subnet.
resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
}

# Private subnets send outside traffic through the NAT instead.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# S3 traffic from the private subnets takes this endpoint instead of the NAT, so image and WAV
# transfers stay on the AWS network and are not billed as NAT data.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
}

# ---- Security groups (firewalls) ----

# The load balancer accepts HTTPS from anyone.
resource "aws_security_group" "alb" {
  name   = "${var.app_name}-alb"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  # protocol -1 means all traffic out is allowed.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Every ECS task shares this group. Port 4000 is open only to the load balancer.
resource "aws_security_group" "tasks" {
  name   = "${var.app_name}-tasks"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "GraphQL API from the load balancer"
    from_port       = 4000
    to_port         = 4000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  # One rule per internal service port. self = true means only other tasks in this same group can
  # connect, which is how the worker reaches cpp-core, ml and audio-producer.
  dynamic "ingress" {
    for_each = { cpp-core = 8080, ml = 5000, audio-producer = 9001 }
    content {
      description = "Worker to ${ingress.key}"
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      self        = true
    }
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# MySQL only accepts connections from the tasks group (the api, worker and migrate tasks).
resource "aws_security_group" "db" {
  name   = "${var.app_name}-db"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "MySQL from the API and worker"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.tasks.id]
  }
}

# ---- Load balancer ----

# The public HTTPS front door for the GraphQL API. Its URL is the api_url output in outputs.tf.
resource "aws_lb" "api" {
  name               = "${var.app_name}-api"
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]

  drop_invalid_header_fields = true
}

# Where the load balancer sends requests: the api task's IP on port 4000 (registered by the
# load_balancer block in ecs.tf). /health is the route in api/src/api.ts.
resource "aws_lb_target_group" "api" {
  name        = "${var.app_name}-api"
  port        = 4000
  protocol    = "HTTP"
  target_type = "ip" # Fargate tasks need ip targets
  vpc_id      = aws_vpc.main.id

  health_check {
    path = "/health"
  }
}

# HTTPS on 443 with the ACM certificate, TLS 1.2 and 1.3 only. TLS ends here, so the task itself
# only speaks plain HTTP inside the VPC.
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
