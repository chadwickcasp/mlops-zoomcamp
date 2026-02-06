# 

resource "aws_iam_role" "iam_lambda" {
  name               = "iam_lambda_${var.lambda_function_name}"
  assume_role_policy = <<EOF
  {
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": [
          "lambda.amazonaws.com",
          "kinesis.amazonaws.com"
        ]
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
  }
  EOF
}

resource "aws_iam_policy" "kinesis_processing" {
  name        = "kinesis_processing_${var.lambda_function_name}"
  path        = "/"
  description = "IAM policy for logging from a Lambda function"
  policy      = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "kinesis:ListStreams",
          "kinesis:ListShards",
          "kinesis:*"
        ],
        "Effect": "Allow",
        "Resource": "arn:aws:kinesis:*:*:*"
      },
      { 
        "Action": [
          "stream:GetRecord",
          "stream:GetShardIterator",
          "stream:DescribeStream",
          "stream:*"
        ],
        "Resource": "arn:aws:stream:*:*:*",
        "Effect": "Allow"
      }
    ]
  }
  EOF
}

resource "aws_iam_role_policy_attachment" "kinesis_processing" {
  role       = aws_iam_role.iam_lambda.name
  policy_arn = aws_iam_policy.kinesis_processing.arn
}

resource "aws_iam_role_policy" "inline_lambda_policy" {
  name       = "LambdaInlinePolicy"
  role       = aws_iam_role.iam_lambda.id
  depends_on = [aws_iam_role.iam_lambda]
  # As created, this policy references the output stream ARN, which is not yet created
  # This will be handled in the main.tf file (probably with a depends_on)
  policy = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "kinesis:PutRecords",
          "kinesis:PutRecord"
        ],
        "Effect": "Allow",
        "Resource": "${var.output_stream_arn}"
      }
      ]
    }
    EOF
}

# IAM for CloudWatch Logging
resource "aws_lambda_permission" "allow_cloudwatch_to_trigger_lambda_function" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.kinesis_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = var.source_stream_arn
}

resource "aws_iam_policy" "allow_logging" {
  name        = "allow_logging_${var.lambda_function_name}"
  path        = "/"
  description = "IAM policy for logging from a Lambda function"
  policy      = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Effect": "Allow",
        "Resource": "arn:aws:logs:*:*:*"
      }
    ]
  }
  EOF
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.iam_lambda.name
  policy_arn = aws_iam_policy.allow_logging.arn
}

# IAM for S3 bucket

resource "aws_iam_policy" "allow_s3_bucket" {
  name        = "lambda_s3_policy_${var.lambda_function_name}"
  description = "IAM policy for accessing a S3 bucket"
  # Attach bucket information, permissions for specific model bucket, and permissions for CloudWatch and Auto Scaling
  policy = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      { 
        "Action": [
          "s3:ListAllMyBuckets",
          "s3:GetBucketLocation",
          "s3:*"
        ],
        "Effect": "Allow",
        "Resource": "*"
      },
      {
        "Action": "s3:*",
        "Effect": "Allow",
        "Resource": [
          "arn:aws:s3:::${var.model_bucket}",
          "arn:aws:s3:::${var.model_bucket}/*"
        ]
      },
      {
        "Action": [
          "autoscaling:Describe*",
          "cloudwatch:*",
          "logs:*",
          "sns:*"
        ],
        "Effect": "Allow",
        "Resource": "*"
      }
    ]
  }
  EOF
}

resource "aws_iam_role_policy_attachment" "allow_s3_bucket" {
  role       = aws_iam_role.iam_lambda.name
  policy_arn = aws_iam_policy.allow_s3_bucket.arn
}
