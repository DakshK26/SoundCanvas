# Terraform settings. State lives in S3 so the whole team (and the deploy workflow) shares one copy.
terraform {
  required_version = ">= 1.10" # the first version with S3-native state locking

  backend "s3" {
    bucket       = "soundcanvas-terraform-state-dk"
    key          = "prototype/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true # a lock file next to the state stops two applies running at once
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
