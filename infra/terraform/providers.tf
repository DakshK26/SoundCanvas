# Terraform entry: the AWS provider and the remote state in S3.
# The state bucket must exist before `terraform init`.
terraform {
  required_version = ">= 1.10" # for use_lockfile

  # State is kept in S3 rather than on one laptop, so local applies and deploy.yml share it.
  # use_lockfile writes a lock object next to it, so two applies can't run at once.
  backend "s3" {
    bucket       = "soundcanvas-terraform-state-dk"
    key          = "prototype/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }

  # ~> 5.81 allows any 5.x from 5.81 up, but not 6.0.
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.81"
    }
  }
}

# Every resource gets a Project tag, so the costs can be filtered in the billing console.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = { Project = var.app_name }
  }
}
