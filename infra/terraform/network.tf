# networking. VPC over 2 AZs, public ALB for the api, everything else private
#
# public subnets:  ALB, NAT gateway
# private subnets: all ECS tasks + RDS (nothing here is reachable from outside the VPC)

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2) # 2 = minimum the ALB + RDS subnet group will take
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true # Cloud Map private DNS (cpp-core.soundcanvas.local) doesn't resolve w/o this
  tags                 = { Name = var.app_name }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  availability_zone       = local.azs[count.index]
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index) # 10.0.0.0/24, 10.0.1.0/24
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.app_name}-public-${count.index}" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  availability_zone = local.azs[count.index]
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 10) # 10.0.10.0/24, 10.0.11.0/24
  tags              = { Name = "${var.app_name}-private-${count.index}" }
}

# public subnets -> internet gateway directly
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

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

# private subnets go out thru a NAT (pull from ECR, call SQS, etc).
# only 1 NAT in 1 AZ to save money - if that AZ dies, tasks lose outbound until it's back.
# NAT per AZ fixes that but it's ~$32/mo EACH. not worth it for a prototype
resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
}

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

# S3 gateway endpoint = free. without it every image + wav goes thru the NAT, which charges per GB
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
}

# security groups:
#   internet -> ALB only (443)
#   ALB -> api only (4000)
#   tasks -> each other only on the service ports
# inside the VPC it's plain http, TLS ends at the ALB. fine bc it never leaves the private subnets
resource "aws_security_group" "alb" {
  name   = "${var.app_name}-alb"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

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

resource "aws_security_group" "db" {
  name   = "${var.app_name}-db"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "MySQL from the gateway API and worker"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.tasks.id]
  }
}

# ALB: https in -> gateway api tasks
resource "aws_lb" "api" {
  name               = "${var.app_name}-api"
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]

  drop_invalid_header_fields = true # off by default for some reason. drops malformed headers (request smuggling stuff)
}

resource "aws_lb_target_group" "api" {
  name        = "${var.app_name}-api"
  port        = 4000
  protocol    = "HTTP"
  target_type = "ip" # has to be ip for fargate (awsvpc), "instance" won't work
  vpc_id      = aws_vpc.main.id

  health_check {
    path = "/health" # plain express route in api.ts, not graphql
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06" # TLS 1.2 + 1.3 only (AWS's recommended one)

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
