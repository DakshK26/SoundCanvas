# Terraform settings. State lives in S3 so the whole team shares one copy.
terraform {
  required_version = ">= 1.5"

  backend "s3" {
    bucket = "soundcanvas-terraform-state-dk"
    key    = "prototype/terraform.tfstate"
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

  default_tags {
    tags = { Project = var.app_name }
  }
}
