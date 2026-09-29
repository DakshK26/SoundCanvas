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
  description = "ACM certificate for the API's HTTPS listener."
  type        = string
}

variable "image_tag" {
  description = "Image tag to deploy from each ECR repository: the git commit SHA."
  type        = string
}

variable "github_repository" {
  description = "The GitHub repository (owner/name) whose deploy workflow may assume the deploy role."
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
