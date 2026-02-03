cd /Users/chadcasper/Documents/MLOps\ Zoomcamp/mlops-zoomcamp/06-best-practices/code/infrastructure && python3 << 'PYTHON_EOF'
content = """# Terraform Infrastructure Explained

## The Big Picture: What Problem Are We Solving?

When deploying ML models to production, you need to provision and manage AWS infrastructure:
- **Kinesis streams** for real-time data ingestion
- **Lambda functions** to process data and make predictions
- **ECR repositories** to store Docker images
- **S3 buckets** to store model artifacts
- **IAM roles and policies** for secure access

**Manual provisioning** (clicking through AWS Console) is:
- ❌ Error-prone (easy to misconfigure)
- ❌ Not reproducible (hard to recreate environments)
- ❌ Not version-controlled (can't track changes)
- ❌ Time-consuming (takes hours to set up)

**Terraform** solves this by:
- ✅ **Infrastructure as Code**: Define infrastructure in version-controlled files
- ✅ **Idempotent**: Run the same code multiple times safely
- ✅ **Reproducible**: Create identical environments (dev, staging, prod)
- ✅ **Automated**: Provision everything with one command

---

## Core Terraform Concepts Used in This Project

### 1. **Terraform Configuration Files**

Terraform uses `.tf` files written in **HCL (HashiCorp Configuration Language)**:

```hcl
# This is a resource block
resource "aws_s3_bucket" "s3_bucket" {
  bucket = "my-bucket-name"
}
```

**Key syntax:**
- `resource "TYPE" "NAME"` - Declares a resource
- `variable "NAME"` - Declares an input variable
- `output "NAME"` - Declares an output value
- `module "NAME"` - References a module
- `${var.name}` - Variable interpolation
- `"${var.prefix}-${var.suffix}"` - String concatenation

---

### 2. **Backend: Remote State Storage**

**Location**: `main.tf` lines 2-9

```hcl
terraform {
  backend "s3" {
    bucket  = "tf-state-mlops-remote433"
    key     = "mlops-zoomcamp-stg.tfstate"
    region  = "us-west-1"
    encrypt = true
  }
}
```

**What it does:**
- Stores Terraform's **state file** (which resources exist) in S3
- **Why remote?** Multiple team members can work on the same infrastructure
- **Why encrypted?** State contains sensitive data (ARNs, IDs)

**Key Concept:**
- Terraform state tracks: "What resources do I manage?"
- Without state, Terraform doesn't know what exists vs. what to create
- State file is the **source of truth**

---

### 3. **Providers**

**Location**: `main.tf` lines 12-14

```hcl
provider "aws" {
  region = var.aws_region
}
```

**What it does:**
- Tells Terraform: "Use the AWS provider"
- Configures which AWS region to use
- Terraform downloads the provider plugin automatically

**Providers available:**
- `aws` - AWS resources
- `null` - Used for running local commands (see ECR module)
- `docker` - Docker resources
- Many more...

---

### 4. **Data Sources**

**Location**: `main.tf` line 16

```hcl
data "aws_caller_identity" "current_identity" {}
```

**What it does:**
- **Reads** information from AWS (doesn't create anything)
- Gets your AWS account ID dynamically
- Used later: `local.account_id = data.aws_caller_identity.current_identity.account_id`

**Why use data sources?**
- Avoid hardcoding values (like account ID)
- Makes code portable across AWS accounts

---

### 5. **Locals**

**Location**: `main.tf` lines 18-20

```hcl
locals {
  account_id = data.aws_caller_identity.current_identity.account_id
}
```

**What it does:**
- Creates **local variables** (not inputs/outputs)
- Computed values used within the configuration
- Example: `"${var.model_bucket}-${var.project_id}-${local.account_id}"`

**Why locals?**
- Avoid repeating complex expressions
- Makes code more readable

---

### 6. **Variables**

**Location**: `variables.tf` and `vars/stg.tfvars`

**Two types:**

#### A. **Variable Declarations** (`variables.tf`)
```hcl
variable "source_stream_name" {
  description = ""
}
```

#### B. **Variable Values** (`vars/stg.tfvars`)
```hcl
source_stream_name = "stg_ride_events"
```

**How they work:**
- Declarations define **what** variables exist
- `.tfvars` files provide **values** for those variables
- Pass values: `terraform apply -var-file=vars/stg.tfvars`

**Why separate?**
- Different environments (dev, staging, prod) use different `.tfvars` files
- Same code, different configurations

---

### 7. **Modules**

**Location**: `main.tf` lines 23-63

```hcl
module "source_kinesis_stream" {
  source      = "./modules/kinesis"
  stream_name = "${var.source_stream_name}-${var.project_id}"
  shard_count = 2
}
```

**What modules do:**
- **Reusable components** - Like functions in programming
- Encapsulate related resources
- Take inputs (variables), produce outputs

**Why modules?**
- **DRY (Don't Repeat Yourself)**: Reuse code for similar resources
- **Organization**: Group related resources together
- **Abstraction**: Hide complexity, expose simple interface

**Example:**
- `modules/kinesis` - Creates a Kinesis stream
- Used twice: once for source stream, once for output stream
- Same code, different inputs

---

### 8. **Resources**

**Location**: Inside modules (e.g., `modules/kinesis/main.tf`)

```hcl
resource "aws_kinesis_stream" "stream" {
  name             = var.stream_name
  shard_count      = var.shard_count
  retention_period = var.retention_period
}
```

**What resources do:**
- **Create** actual AWS resources
- Terraform manages the lifecycle (create, update, destroy)
- Each resource has a **type** (`aws_kinesis_stream`) and **name** (`stream`)

**Resource naming:**
- `aws_kinesis_stream.stream` - Reference within Terraform
- `name = var.stream_name` - Actual AWS resource name

---

### 9. **Outputs**

**Location**: Inside modules (e.g., `modules/kinesis/main.tf` line 13)

```hcl
output "stream_arn" {
  value = aws_kinesis_stream.stream.arn
}
```

**What outputs do:**
- **Expose** values from modules/resources
- Other modules can reference: `module.source_kinesis_stream.stream_arn`
- Useful for passing data between modules

**Example flow:**
1. Kinesis module creates stream → outputs ARN
2. Lambda module needs ARN → references `module.source_kinesis_stream.stream_arn`

---

### 10. **Dependencies**

**Implicit dependencies:**
```hcl
module "lambda_function" {
  image_uri = module.ecr.image_uri  # Lambda depends on ECR
}
```
- Terraform automatically detects: "Lambda needs ECR output, so build ECR first"

**Explicit dependencies:**
```hcl
depends_on = [aws_iam_role_policy_attachment.kinesis_processing]
```
- Sometimes Terraform can't infer dependencies
- `depends_on` forces order

---

## Project Structure

```
infrastructure/
├── main.tf                    # Root configuration, module calls
├── variables.tf               # Root-level variable declarations
├── vars/
│   └── stg.tfvars            # Staging environment values
├── modules/
│   ├── kinesis/
│   │   ├── main.tf           # Kinesis stream resource
│   │   └── variables.tf      # Module inputs
│   ├── s3/
│   │   ├── main.tf           # S3 bucket resource
│   │   └── variables.tf      # Module inputs
│   ├── ecr/
│   │   ├── main.tf           # ECR repo + Docker build/push
│   │   └── variables.tf       # Module inputs
│   └── lambda/
│       ├── main.tf           # Lambda function + event mapping
│       ├── iam.tf            # IAM roles and policies
│       └── variables.tf      # Module inputs
└── .terraform/                # Terraform cache (auto-generated)
```

**Design Pattern:**
- **Root** (`main.tf`) = Orchestration (calls modules, wires them together)
- **Modules** = Implementation (actual resources)
- **Separation**: Each module is self-contained

---

## Module-by-Module Breakdown

### Module 1: Kinesis Stream (`modules/kinesis/`)

**Purpose**: Create Kinesis data streams for real-time data processing

**Resources Created:**
- `aws_kinesis_stream` - The actual Kinesis stream

**Key Configuration:**
```hcl
shard_count = 2              # Parallelism (more shards = more throughput)
retention_period = 48        # Hours to keep data (for replay)
```

**Why 2 shards?**
- Each shard can handle ~1MB/sec write, ~2MB/sec read
- 2 shards = ~2MB/sec total throughput
- Trade-off: More shards = more cost, more parallelism

**Outputs:**
- `stream_arn` - Used by Lambda to connect to the stream

**Used Twice:**
- `source_kinesis_stream` - Input stream (ride events)
- `output_kinesis_stream` - Output stream (predictions)

---

### Module 2: S3 Bucket (`modules/s3/`)

**Purpose**: Store MLflow model artifacts

**Resources Created:**
- `aws_s3_bucket` - The S3 bucket

**Key Design Decision:**
```hcl
bucket_name = "${var.model_bucket}-${var.project_id}-${local.account_id}"
```

**Why include account_id?**
- S3 bucket names are **globally unique** across ALL AWS accounts
- Someone else might have `stg-mlflow-models-mlops-zoomcamp`
- Adding account ID ensures uniqueness: `stg-mlflow-models-mlops-zoomcamp-413093438819`

**Outputs:**
- `name` - Bucket name (used by Lambda environment variable)

---

### Module 3: ECR Repository (`modules/ecr/`)

**Purpose**: Store Docker images for Lambda functions

**Resources Created:**
- `aws_ecr_repository` - ECR repository
- `null_resource.ecr_image` - Triggers Docker build/push
- `data.aws_ecr_image` - Waits for image to exist

**Key Concept: `null_resource`**

```hcl
resource "null_resource" "ecr_image" {
  triggers = {
    python_file = md5(file(var.lambda_function_local_path))
    dockerfile  = md5(file(var.dockerfile_local_path))
    platform    = "linux/amd64"
  }
  
  provisioner "local-exec" {
    command = "docker buildx build --platform linux/amd64 ..."
  }
}
```

**What it does:**
- `null_resource` = Doesn't create an AWS resource
- `provisioner "local-exec"` = Runs commands on your local machine
- `triggers` = Rebuilds when files change (MD5 hash changes)

**Why `null_resource`?**
- Terraform doesn't have native Docker build support
- We need to build Docker image **during** Terraform apply
- `null_resource` bridges Terraform ↔ Docker

**The Build Process:**
1. Terraform detects file changes (via triggers)
2. Runs `docker buildx build --platform linux/amd64`
3. Builds image for Lambda (must be linux/amd64, not arm64)
4. Pushes to ECR
5. `data.aws_ecr_image` waits for image to exist
6. Outputs image URI for Lambda

**Why `--platform linux/amd64`?**
- Lambda runs on x86_64 architecture
- Your Mac might be ARM64
- `buildx` cross-compiles for the target platform

**Outputs:**
- `image_uri` - Full ECR image URI (e.g., `413093438819.dkr.ecr.us-west-1.amazonaws.com/repo:latest`)

---

### Module 4: Lambda Function (`modules/lambda/`)

**Purpose**: Serverless function to process Kinesis events and make predictions

**Resources Created:**

#### A. **Lambda Function** (`main.tf`)
```hcl
resource "aws_lambda_function" "kinesis_lambda" {
  function_name = var.lambda_function_name
  image_uri     = var.image_uri
  package_type  = "Image"
  role          = aws_iam_role.iam_lambda.arn
  timeout       = 180
  environment {
    variables = {
      PREDICTIONS_STREAM_NAME = var.output_stream_name
      MODEL_BUCKET            = var.model_bucket
    }
  }
}
```

**Key Configuration:**
- `package_type = "Image"` - Uses Docker image (not ZIP)
- `timeout = 180` - 3 minutes max execution time
- `environment.variables` - Passes config to Lambda code

#### B. **Event Source Mapping** (`main.tf`)
```hcl
resource "aws_lambda_event_source_mapping" "kinesis_lambda_event_source_mapping" {
  function_name     = aws_lambda_function.kinesis_lambda.arn
  event_source_arn  = var.source_stream_arn
  starting_position = "LATEST"
}
```

**What it does:**
- **Connects** Kinesis stream to Lambda
- Lambda automatically invokes when new records arrive in Kinesis
- `starting_position = "LATEST"` - Only process new records (not historical)

**Why Event Source Mapping?**
- Without it: Lambda doesn't know about Kinesis
- With it: AWS automatically invokes Lambda on new Kinesis records

#### C. **IAM Roles and Policies** (`iam.tf`)

**Three policies:**

1. **Kinesis Processing Policy**
   - Allows Lambda to read from source stream
   - Allows Lambda to write to output stream

2. **Logging Policy**
   - Allows Lambda to write CloudWatch logs
   - Required for debugging

3. **S3 Policy**
   - Allows Lambda to read model artifacts from S3
   - Used to load MLflow models

**IAM Role:**
```hcl
resource "aws_iam_role" "iam_lambda" {
  assume_role_policy = <<EOF
  {
    "Principal": {
      "Service": ["lambda.amazonaws.com"]
    }
  }
  EOF
}
```

**What it does:**
- Creates a role Lambda can "assume"
- Lambda uses this role to access AWS services
- Policies attached to role grant permissions

**Why IAM?**
- Lambda needs permissions to:
  - Read from Kinesis
  - Write to Kinesis
  - Read from S3
  - Write logs
- IAM policies grant these permissions

---

## Data Flow: How Everything Connects

### Infrastructure Creation Flow

```
1. Terraform Apply Starts
        │
        ▼
2. Create Kinesis Streams
   ┌────────────────────┐      ┌────────────────────┐
   │ Source Stream      │      │ Output Stream       │
   │ (ride_events)      │      │ (ride_predictions)  │
   └────────────────────┘      └────────────────────┘
        │                              │
        │                              │
        ▼                              ▼
3. Create S3 Bucket             4. Create ECR Repo
   ┌────────────────────┐      ┌────────────────────┐
   │ Model Artifacts    │      │ Docker Images       │
   │ (MLflow models)    │      │ (Lambda container) │
   └────────────────────┘      └──────────┬─────────┘
                                          │
                                          ▼
                                   5. Build & Push Image
                                   (null_resource triggers)
                                          │
                                          ▼
                                   6. Create Lambda Function
                                   ┌────────────────────┐
                                   │ Lambda Function    │
                                   │ (Uses ECR image)   │
                                   └──────────┬─────────┘
                                              │
                                              ▼
                                   7. Create Event Source Mapping
                                   (Connects Kinesis → Lambda)
                                              │
                                              ▼
                                   8. Attach IAM Policies
                                   (Grants permissions)
```

### Runtime Flow (After Infrastructure is Created)

```
1. Ride events arrive in Source Kinesis Stream
        │
        ▼
2. Event Source Mapping triggers Lambda
        │
        ▼
3. Lambda function:
   - Reads event from Kinesis
   - Loads model from S3 (using MODEL_BUCKET env var)
   - Makes prediction
   - Writes prediction to Output Kinesis Stream
   - Uses PREDICTIONS_STREAM_NAME env var
```

---

## Key Design Decisions & Assumptions

### 1. **Modular Architecture**

**Decision**: Split infrastructure into modules (kinesis, s3, ecr, lambda)

**Why:**
- **Reusability**: Kinesis module used twice (source + output)
- **Maintainability**: Changes to one module don't affect others
- **Testability**: Can test modules independently

**Trade-off:**
- More files to manage
- But easier to understand and modify

---

### 2. **Remote State in S3**

**Decision**: Store Terraform state in S3 (not local file)

**Why:**
- **Team collaboration**: Multiple people can work on the same infrastructure
- **Backup**: State is stored safely in S3
- **Locking**: Prevents concurrent modifications

**Assumption:**
- S3 bucket `tf-state-mlops-remote433` already exists
- You have permissions to read/write to it

---

### 3. **Environment-Specific Variables**

**Decision**: Use `.tfvars` files for different environments

**Why:**
- Same code, different configs
- Easy to create dev/staging/prod environments

**Example:**
- `vars/stg.tfvars` - Staging environment
- `vars/prod.tfvars` - Production (would have different values)

**Assumption:**
- Environment naming convention: `stg_*` for staging

---

### 4. **Globally Unique Resource Names**

**Decision**: Include account ID in resource names

**Why:**
- S3 bucket names must be globally unique
- Prevents conflicts with other AWS accounts

**Example:**
- `stg-mlflow-models-mlops-zoomcamp-413093438819`

**Trade-off:**
- Longer names
- But guaranteed uniqueness

---

### 5. **Docker Image Build During Apply**

**Decision**: Build Docker image as part of Terraform apply

**Why:**
- Ensures Lambda always has latest code
- Single command (`terraform apply`) does everything

**Trade-off:**
- Slower applies (builds Docker image)
- But simpler workflow

**Alternative:**
- Build image in CI/CD pipeline
- Terraform just references existing image
- Faster applies, but more complex setup

---

### 6. **Cross-Platform Docker Builds**

**Decision**: Use `docker buildx` with `--platform linux/amd64`

**Why:**
- Lambda requires x86_64 architecture
- Your Mac might be ARM64
- `buildx` handles cross-compilation

**Assumption:**
- Docker buildx is available
- You're building on a different architecture than Lambda runs

---

### 7. **IAM Policy Design**

**Decision**: Separate policies for different permissions

**Why:**
- **Principle of Least Privilege**: Grant only what's needed
- **Maintainability**: Easier to update specific permissions
- **Auditability**: Clear what each policy does

**Policies:**
- `kinesis_processing` - Kinesis read/write
- `allow_logging` - CloudWatch logs
- `allow_s3_bucket` - S3 model access

**Trade-off:**
- More policies to manage
- But better security and clarity

---

### 8. **Event Source Mapping Configuration**

**Decision**: `starting_position = "LATEST"`

**Why:**
- Only process new events (not historical backlog)
- Prevents Lambda from processing old data on first deploy

**Alternative:**
- `TRIM_HORIZON` - Process all data from beginning
- Useful for backfilling, but can overwhelm Lambda

---

### 9. **Lambda Timeout**

**Decision**: `timeout = 180` (3 minutes)

**Why:**
- Model loading from S3 can take time
- Prediction processing might be slow
- 3 minutes provides buffer

**Trade-off:**
- Longer timeout = more cost if function hangs
- But prevents premature timeouts

---

### 10. **No Lambda Handler/Runtime**

**Decision**: `package_type = "Image"` (no handler specified)

**Why:**
- Docker image-based Lambda
- Handler/runtime configured in Dockerfile
- More flexible than ZIP-based Lambda

**Assumption:**
- Dockerfile sets `CMD` or `ENTRYPOINT` correctly
- Image follows Lambda container image format

---

## Terraform Workflow

### Initial Setup

```bash
cd infrastructure
terraform init          # Download providers, modules
```

**What happens:**
- Downloads AWS provider plugin
- Initializes backend (S3)
- Downloads modules (if remote)

---

### Planning Changes

```bash
terraform plan -var-file=vars/stg.tfvars
```

**What happens:**
- Reads current state from S3
- Compares to desired state (your `.tf` files)
- Shows what will be created/changed/destroyed
- **Doesn't make changes** (dry run)

**Output:**
```
Plan: 5 to add, 0 to change, 0 to destroy.
```

---

### Applying Changes

```bash
terraform apply -var-file=vars/stg.tfvars
```

**What happens:**
1. Shows plan (same as `terraform plan`)
2. Asks for confirmation
3. Creates/updates/destroys resources
4. Updates state file in S3

**Order of operations:**
- Terraform determines dependency graph
- Creates resources in correct order
- Example: ECR → Docker build → Lambda (Lambda needs ECR image)

---

### Destroying Infrastructure

```bash
terraform destroy -var-file=vars/stg.tfvars
```

**What happens:**
- Destroys all resources created by Terraform
- **Warning**: This deletes everything!

**Note:**
- Some resources can't be destroyed if they contain data
- ECR repo with images → must delete images first or use `force_delete`

---

## Common Terraform Concepts Explained

### State File

**What it is:**
- JSON file tracking what Terraform manages
- Maps Terraform resources to AWS resource IDs

**Example:**
```json
{
  "resources": [{
    "type": "aws_kinesis_stream",
    "name": "stream",
    "instances": [{
      "attributes": {
        "id": "arn:aws:kinesis:us-west-1:413093438819:stream/stg_ride_events-mlops-zoomcamp"
      }
    }]
  }]
}
```

**Why important:**
- Terraform uses state to know: "Does this resource exist?"
- Without state, Terraform would try to create everything again

---

### Resource Addressing

**How to reference resources:**

```hcl
# Within same file:
aws_kinesis_stream.stream.arn

# From module:
module.source_kinesis_stream.stream_arn

# From data source:
data.aws_caller_identity.current_identity.account_id
```

**Pattern:**
- `RESOURCE_TYPE.RESOURCE_NAME.ATTRIBUTE`
- `module.MODULE_NAME.OUTPUT_NAME`

---

### Variable Interpolation

**String concatenation:**
```hcl
"${var.prefix}-${var.suffix}-${local.account_id}"
```

**Result:** `"stg-mlflow-models-mlops-zoomcamp-413093438819"`

**When to use `${}`:**
- Inside strings: `"${var.name}"`
- Outside strings: `var.name` (no quotes needed)

---

### Dependencies

**Terraform automatically detects:**

```hcl
module "lambda" {
  image_uri = module.ecr.image_uri  # Lambda depends on ECR
}
```

**Terraform will:**
1. Create ECR first
2. Build/push Docker image
3. Then create Lambda

**Explicit dependencies:**
```hcl
depends_on = [aws_iam_role_policy_attachment.kinesis_processing]
```

**When to use:**
- Terraform can't infer dependency
- Need to force order

---

## Troubleshooting Common Issues

### Issue: "Resource already exists"

**Cause:** Resource exists in AWS but not in Terraform state

**Fix:**
```bash
terraform import aws_s3_bucket.s3_bucket stg-mlflow-models-mlops-zoomcamp-413093438819
```

**What it does:**
- Adds existing resource to Terraform state
- Terraform now "knows" about it

---

### Issue: "State locked"

**Cause:** Another `terraform apply` is running

**Fix:**
- Wait for other apply to finish
- Or: Check S3 for stale lock files

---

### Issue: "Module not installed"

**Cause:** Haven't run `terraform init`

**Fix:**
```bash
terraform init
```

---

### Issue: "InvalidParameterValueException: image manifest not supported"

**Cause:** Docker image is wrong architecture (ARM64 instead of AMD64)

**Fix:**
- Use `docker buildx build --platform linux/amd64`
- Ensure `--load` flag is used before `docker push`

---

### Issue: "Circular dependency"

**Cause:** Module A depends on Module B, Module B depends on Module A

**Fix:**
- Restructure to break cycle
- Use `depends_on` carefully
- Example: Removed `integration_test` from `build` dependencies

---

## Best Practices Used in This Project

### 1. **Version Constraints**

```hcl
terraform {
  required_version = ">=1.0"
}
```

**Why:**
- Ensures everyone uses compatible Terraform version
- Prevents version-specific bugs

---

### 2. **Variable Defaults**

```hcl
variable "aws_region" {
  default = "us-west-1"
}
```

**Why:**
- Sensible defaults reduce required inputs
- Can still override with `.tfvars`

---

### 3. **Descriptive Names**

```hcl
module "source_kinesis_stream"  # Clear: this is the source stream
module "output_kinesis_stream"  # Clear: this is the output stream
```

**Why:**
- Self-documenting code
- Easier to understand

---

### 4. **Outputs for Integration**

```hcl
output "stream_arn" {
  value = aws_kinesis_stream.stream.arn
}
```

**Why:**
- Modules expose what other modules need
- Enables module composition

---

### 5. **Environment Separation**

```
vars/
  ├── stg.tfvars    # Staging values
  └── prod.tfvars   # Production values (future)
```

**Why:**
- Same code, different configs
- Easy to manage multiple environments

---

## Summary: What This Infrastructure Does

This Terraform configuration creates a **serverless ML prediction pipeline**:

1. **Kinesis Streams** - Real-time data ingestion (input + output)
2. **S3 Bucket** - Stores MLflow model artifacts
3. **ECR Repository** - Stores Docker images for Lambda
4. **Lambda Function** - Processes Kinesis events, makes predictions
5. **IAM Roles/Policies** - Grants necessary permissions
6. **Event Source Mapping** - Connects Kinesis to Lambda

**The Flow:**
```
Ride Events → Kinesis Source Stream → Lambda Function → Predictions → Kinesis Output Stream
                                      ↓
                                 Load Model from S3
```

**Key Benefits:**
- ✅ **Infrastructure as Code**: Version-controlled, reproducible
- ✅ **Modular**: Easy to understand and modify
- ✅ **Automated**: One command provisions everything
- ✅ **Scalable**: Serverless architecture scales automatically

---

## Next Steps & Learning Resources

### To Learn More:

1. **Terraform Documentation**: https://www.terraform.io/docs
2. **AWS Provider Docs**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
3. **Terraform Best Practices**: https://www.terraform.io/docs/cloud/guides/recommended-practices

### Common Commands:

```bash
terraform init              # Initialize workspace
terraform plan              # Preview changes
terraform apply             # Apply changes
terraform destroy           # Destroy infrastructure
terraform fmt               # Format code
terraform validate          # Validate syntax
terraform state list        # List managed resources
terraform show              # Show current state
```

### To Extend This:

- Add more environments (dev, prod)
- Add monitoring (CloudWatch alarms)
- Add VPC configuration (if Lambda needs VPC access)
- Add CI/CD integration (GitHub Actions, GitLab CI)
- Add Terraform Cloud for team collaboration

---

## Questions & Answers

### Q: Why not use AWS CDK or CloudFormation?

**A:** Terraform is:
- **Provider-agnostic**: Works with AWS, GCP, Azure, etc.
- **Simpler syntax**: HCL is easier to read than CloudFormation JSON/YAML
- **Better state management**: Handles state more gracefully
- **Widely adopted**: Large community, lots of modules

**Trade-off:** CloudFormation is AWS-native, but Terraform is more portable.

---

### Q: What happens if I manually delete a resource in AWS Console?

**A:** Terraform will detect it's missing on next `terraform apply` and recreate it. This is why you should **always** use Terraform to manage resources it created.

---

### Q: Can I modify resources manually and keep Terraform in sync?

**A:** Not recommended. Terraform will overwrite manual changes on next apply. Use Terraform for all changes.

---

### Q: Why use `null_resource` for Docker builds?

**A:** Terraform doesn't have native Docker support. `null_resource` with `local-exec` bridges Terraform and Docker. Alternative: Use `terraform-provider-docker` or build in CI/CD.

---

### Q: What's the difference between `variable` and `local`?

**A:**
- **`variable`**: Input from outside (`.tfvars` file, command line)
- **`local`**: Computed value inside Terraform (derived from data sources, variables)

---

### Q: Why separate modules instead of one big file?

**A:**
- **Reusability**: Use Kinesis module twice
- **Maintainability**: Changes isolated to one module
- **Testability**: Test modules independently
- **Clarity**: Each module has single responsibility

---

This infrastructure provides a **production-ready, serverless ML pipeline** that's:
- ✅ Fully automated
- ✅ Version-controlled
- ✅ Reproducible
- ✅ Scalable
- ✅ Maintainable
"""

with open('TERRAFORM_EXPLAINED.md', 'w') as f:
    f.write(content)
print("File created successfully!")
PYTHON_EOF

