# state in S3 (not local) so my laptop and the deploy workflow use the same copy.
# NOTE: the state bucket has to exist before `terraform init`, terraform can't create its own backend
terraform {
  required_version = ">= 1.10" # 1.10+ = S3 can lock by itself, no dynamodb table needed anymore

  backend "s3" {
    bucket       = "soundcanvas-terraform-state-dk"
    key          = "prototype/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true # .tflock file next to the state -> 2 applies can't run at the same time
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
