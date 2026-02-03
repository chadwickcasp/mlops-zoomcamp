resource "aws_s3_bucket" "s3_bucket" {
  bucket = var.bucket_name
  # ACL is default private in AWS S3 as of 2023
  # acl = "private"
}

output "name" {
  value = aws_s3_bucket.s3_bucket.bucket
}