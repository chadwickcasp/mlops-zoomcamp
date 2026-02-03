resource "aws_lambda_function" "kinesis_lambda" {
  # This doesn't need a handler or runtime because it's an image-based Lambda function
  # and the image is already configured with the handler and runtime in the Dockerfile
  function_name = var.lambda_function_name
  # This can be any image to bootstrap the lambda config, even unrelated to the inference service on ECR
  # which would be updated regularly anyway via CI/CD pipeline
  image_uri    = var.image_uri
  package_type = "Image"
  role         = aws_iam_role.iam_lambda.arn
  tracing_config {
    mode = "Active"
  }

  # This is optional but it's good practice to have it
  # We update the configuration in the CI/CD pipeline anyway
  # TEST_RUN=False so Lambda writes predictions to Kinesis (callbacks not empty)
  environment {
    variables = {
      PREDICTIONS_STREAM_NAME = var.output_stream_name
      MODEL_BUCKET            = var.model_bucket
      TEST_RUN                = "False"
    }
  }
  # Increased timeout to allow model loading from S3 during cold start
  # Model loading can take 3-5 minutes depending on model size and network
  # AWS Lambda max timeout is 900 seconds (15 minutes)
  timeout = 600
  
  # Increased memory to prevent OutOfMemory errors during model loading
  # MLflow models with dependencies can require significant memory
  # More memory also provides more CPU power (proportional allocation)
  memory_size = 512
}

# Kinesis Event Source Mapping
# This prevents the Lambda function from being invoked if the Kinesis stream is empty

resource "aws_lambda_function_event_invoke_config" "kinesis_lambda_event_invoke_config" {
  function_name                = aws_lambda_function.kinesis_lambda.function_name
  maximum_retry_attempts       = 0
  # Increased to allow time for cold start model loading
  # Events can wait up to 6 hours, but we set to 15 minutes to allow for initialization
  maximum_event_age_in_seconds = 900
}

resource "aws_lambda_event_source_mapping" "kinesis_lambda_event_source_mapping" {
  function_name     = aws_lambda_function.kinesis_lambda.arn
  event_source_arn  = var.source_stream_arn
  starting_position = "LATEST"
  enabled           = true
  batch_size        = 10
  depends_on        = [aws_iam_role_policy_attachment.kinesis_processing]
}


