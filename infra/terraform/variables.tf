# Inputs the deploy workflow and a first-time apply have to fill in (bucket, frontend URL,
# certificate, GitHub repo, alarm email).
# Locally they go in terraform.tfvars, one `name = "value"` per line (the file is gitignored).
# .github/workflows/deploy.yml passes the same values as TF_VAR_ environment variables.

variable "aws_region" {
  description = "Region for everything."
  type        = string
  default     = "us-east-2"
}

variable "app_name" {
  description = "Prefix for every resource name."
  type        = string
  default     = "soundcanvas"
}

variable "bucket_name" {
  description = "S3 bucket for uploaded images and generated songs. Bucket names are global, so pick a unique one. Example: \"soundcanvas-media-yourname\"."
  type        = string
}

variable "frontend_origin" {
  description = "The frontend's URL, e.g. https://soundcanvas.vercel.app. Only it may upload to the bucket from a browser."
  type        = string
}

variable "certificate_arn" {
  description = "ACM certificate for the API's HTTPS listener. Example: \"arn:aws:acm:us-east-2:123456789012:certificate/...\"."
  type        = string
}

variable "image_tag" {
  description = "Image tag to deploy from each ECR repository: the git commit SHA. Example: the output of `git rev-parse HEAD`."
  type        = string
}

variable "github_repository" {
  description = "The GitHub repository (owner/name) whose deploy workflow may assume the deploy role. Example: \"yourname/SoundCanvas\"."
  type        = string
}

variable "alarm_email" {
  description = "Email address for alarm notifications. Leave empty to create the alarms without a subscriber."
  type        = string
  default     = ""
}

variable "deletion_protection" {
  description = "Stops the database being deleted by accident. Set to false before a deliberate `terraform destroy`."
  type        = bool
  default     = true
}
