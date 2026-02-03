variable "aws_region" {
  description = "AWS region to create resources"
  default     = "us-west-1"
}

variable "project_id" {
  description = "project_id"
  default     = "mlops-zoomcamp"
}

variable "source_stream_name" {
  description = ""
}

variable "output_stream_name" {
  description = ""
}

variable "model_bucket" {
  description = "s3 model bucket"
}

variable "ecr_repo_name" {
  description = "ECR repository name"
}

variable "lambda_function_local_path" {
  description = "Python function local path"
}

variable "dockerfile_local_path" {
  description = "Dockerfile local path"
}

variable "lambda_function_name" {
  description = "Lambda function name"
}
