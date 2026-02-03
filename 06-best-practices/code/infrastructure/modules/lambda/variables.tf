variable "source_stream_arn" {
  description = "ARN of the Kinesis stream to read from"
}

variable "source_stream_name" {
  description = "Name of the Kinesis stream to read from"
}

variable "output_stream_arn" {
  description = "ARN of the Kinesis stream to log to"
}

variable "output_stream_name" {
  description = "Name of the Kinesis stream to log to"
}

variable "model_bucket" {
  description = "Name of the S3 bucket to store the model"
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
}

variable "image_uri" {
  description = "URI of the ECR image to use for the Lambda function"
}
