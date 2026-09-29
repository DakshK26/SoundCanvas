# The state bucket must exist before `terraform init`.
terraform {
  required_version = ">= 1.10" # for use_lockfile

  backend "s3" {
    bucket       = "soundcanvas-terraform-state-dk"
    key          = "prototype/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.81"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = { Project = var.app_name }
  }
}
