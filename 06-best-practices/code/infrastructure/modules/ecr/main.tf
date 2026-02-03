resource "aws_ecr_repository" "repo" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }
}

resource "null_resource" "ecr_image" {
  # Triggers the build and push of the ECR image when the Python function or Dockerfile changes
  triggers = {
    python_file = md5(file(var.lambda_function_local_path))
    dockerfile  = md5(file(var.dockerfile_local_path))
    platform    = "linux/amd64"  # Force rebuild when platform changes
  }

  # Allows us to execute the commands on the local machine
  provisioner "local-exec" {
    command = <<EOF
      aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${var.account_id}.dkr.ecr.${var.region}.amazonaws.com
      cd ../
      # Ensure buildx builder exists for cross-platform builds
      docker buildx create --use --name multiplatform-builder 2>/dev/null || docker buildx use multiplatform-builder
      # Build a single-arch linux/amd64 image (Lambda requires x86_64/amd64)
      # --load loads the image into local Docker, then we push it
      docker buildx build --platform linux/amd64 -t ${aws_ecr_repository.repo.repository_url}:${var.ecr_image_tag} --load .
      docker push ${aws_ecr_repository.repo.repository_url}:${var.ecr_image_tag}
    EOF
  }
}

# Wait for the ECR image to be built and pushed before lambda config runs it
data "aws_ecr_image" "lambda_image" {
  depends_on      = [null_resource.ecr_image]
  repository_name = var.ecr_repo_name
  image_tag       = var.ecr_image_tag
}

output "image_uri" {
  value = "${aws_ecr_repository.repo.repository_url}:${data.aws_ecr_image.lambda_image.image_tag}"
}
