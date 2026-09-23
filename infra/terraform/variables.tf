# Inputs. Set the required ones in terraform.tfvars (see terraform.tfvars.example).

variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "app_name" {
  description = "Prefix for every resource name."
  type        = string
  default     = "soundcanvas"
}

variable "bucket_name" {
  description = "S3 bucket for uploaded images and generated songs. Bucket names are global, so pick a unique one."
  type        = string
}

variable "frontend_origin" {
  description = "The frontend's URL, e.g. https://soundcanvas.vercel.app. Only it may upload to the bucket from a browser."
  type        = string
}

variable "certificate_arn" {
  description = "ACM certificate for the API's HTTPS listener. Browsers block an HTTPS site from calling a plain-HTTP API."
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy from each ECR repository."
  type        = string
  default     = "latest"
}
