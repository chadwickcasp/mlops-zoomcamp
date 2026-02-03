# Make sure to create a bucket beforehand
terraform {
  required_version = ">=1.0"
  backend "s3" {
    bucket  = "tf-state-mlops-remote433"
    key     = "mlops-zoomcamp-stg.tfstate"
    region  = "us-west-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current_identity" {}

locals {
  account_id = data.aws_caller_identity.current_identity.account_id
}

# Ride events source stream
module "source_kinesis_stream" {
  source           = "./modules/kinesis"
  stream_name      = "${var.source_stream_name}-${var.project_id}"
  shard_count      = 2
  retention_period = 48
  tags             = var.project_id
}

# Ride events predictions stream
module "output_kinesis_stream" {
  source           = "./modules/kinesis"
  stream_name      = "${var.output_stream_name}-${var.project_id}"
  shard_count      = 2
  retention_period = 48
  tags             = var.project_id
}

# S3 model bucket for model artifacts (account_id ensures globally unique name)
module "s3_bucket" {
  source      = "./modules/s3"
  bucket_name = "${var.model_bucket}-${var.project_id}-${local.account_id}"
}

module "ecr" {
  source                     = "./modules/ecr"
  ecr_repo_name              = "${var.ecr_repo_name}_${var.project_id}"
  account_id                 = local.account_id
  lambda_function_local_path = var.lambda_function_local_path
  dockerfile_local_path      = var.dockerfile_local_path
}

module "lambda_function" {
  source               = "./modules/lambda"
  image_uri            = module.ecr.image_uri
  lambda_function_name = "${var.lambda_function_name}_${var.project_id}"
  model_bucket         = module.s3_bucket.name
  output_stream_name   = "${var.output_stream_name}-${var.project_id}"
  output_stream_arn    = module.output_kinesis_stream.stream_arn
  source_stream_name   = "${var.source_stream_name}-${var.project_id}"
  source_stream_arn    = module.source_kinesis_stream.stream_arn
}
