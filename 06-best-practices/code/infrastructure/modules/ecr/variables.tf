variable "region" {
  type        = string
  description = "The region to deploy the ECR repository to"
  default     = "us-west-1"
}

variable "account_id" {
  description = "The account ID to deploy the ECR repository to"
}

variable "ecr_image_tag" {
  type        = string
  description = "The tag to apply to the ECR image"
  default     = "latest"
}

variable "lambda_function_local_path" {
  type        = string
  description = "The path to the Python function local path"
}

variable "dockerfile_local_path" {
  type        = string
  description = "The path to the Dockerfile local path"
}

variable "ecr_repo_name" {
  type        = string
  description = "The name of the ECR repository"
}
