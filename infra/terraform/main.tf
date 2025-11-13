# SoundCanvas AWS Infrastructure
# NO CREDENTIALS IN THIS FILE - Configure via terraform.tfvars (gitignored)

terraform {
  required_version = ">= 1.0"
  
  backend "s3" {
    # Configure via: terraform init -backend-config="bucket=YOUR_BUCKET"
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

# Variables (values in terraform.tfvars - gitignored)
variable "aws_region" { default = "us-east-2" }
variable "environment" { default = "prod" }
variable "app_name" { default = "soundcanvas" }
variable "db_password" { type = string; sensitive = true }
variable "ecr_gateway_uri" { type = string }
variable "ecr_cpp_core_uri" { type = string }
variable "ecr_audio_producer_uri" { type = string }
variable "s3_uploads_bucket" { type = string }
variable "rds_endpoint" { type = string }

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "${var.app_name}-vpc" }
}

# See full configuration in docs/TERRAFORM_REFERENCE.md
# This is a minimal template - expand as needed for production deployment

output "alb_dns_name" {
  description = "Application Load Balancer DNS"
  value       = "Configure full infrastructure - see documentation"
}
