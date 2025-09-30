# AWS Profile, IAM User, and S3 Setup for MLflow (Project Notes)

This document captures the **exact workflow** we used to set up AWS credentials for this project:
- A **local AWS profile** (for laptop/CLI usage)
- An **IAM Role on EC2** (so the MLflow server can write to S3 without keys)
- An **S3 bucket** for MLflow artifacts
- Minimal verification and troubleshooting

> These steps reflect the **current AWS Console UI** (as of 2025).

---

## 0) Assumptions

- Region: **us-west-1** (adjust as needed).
- You have an EC2 instance running the MLflow server.
- You prefer **IAM Role** on EC2 for S3 access (no long-lived keys on the instance).
- You may also want a **local AWS CLI profile** on your laptop for ad-hoc S3/CLI work.

---

## 1) Install AWS CLI locally

### macOS (Homebrew)
```bash
brew install awscli
aws --version
```

### Linux / Amazon Linux 2
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y unzip
curl -sS "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
aws --version

# Amazon Linux 2 (yum)
sudo yum install -y unzip
curl -sS "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
aws --version
```

---

## 2) Create an IAM **User** for local development (programmatic access)

1. **AWS Console → IAM → Users → Add users**
   - User name: e.g., `mlflow-client`
   - Create the user (no console password).

2. After creation, open the user:
   - **Security credentials** → **Access keys** → **Create access key**
   - Choose **Command Line Interface (CLI)** as the use case
   - Download the `.csv` with **Access Key ID** and **Secret Access Key**

3. **Attach permissions** (choose one):
   - *Testing / quick start*: attach **AmazonS3FullAccess**
   - *Production (recommended)*: attach a **custom inline policy** scoped to your bucket:

     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Sid": "ListOwnBucket",
           "Effect": "Allow",
           "Action": ["s3:ListBucket"],
           "Resource": "arn:aws:s3:::mlflow-artifacts-project"
         },
         {
           "Sid": "RWArtifacts",
           "Effect": "Allow",
           "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject"],
           "Resource": "arn:aws:s3:::mlflow-artifacts-project/*"
         }
       ]
     }
     ```

---

## 3) Configure the **AWS profile** on your laptop

```bash
aws configure --profile mlflow-client
# Paste Access Key ID
# Paste Secret Access Key
# Default region name: us-west-1
# Default output format: json
```

Verify:
```bash
aws sts get-caller-identity --profile mlflow-client
aws s3 ls --profile mlflow-client
```

> **Note:** In your Python code, only set `AWS_PROFILE` if your client needs to talk to AWS.  
> For our MLflow setup, the **server (EC2)** writes to S3 using its role, so the client does **not** need a profile:
> ```python
> import os
> os.environ.pop("AWS_PROFILE", None)  # Ensure it's not set to an invalid value
> ```

---

## 4) Create an S3 bucket for MLflow artifacts

- **S3 → Create bucket** (e.g., `mlflow-artifacts-project`)
- Keep **Block Public Access** **enabled** (default)
- Region: **same as EC2** if possible (e.g., `us-west-1`)

You generally **don’t need a bucket policy** if you rely on IAM policies/roles.  
If needed, a bucket policy restricting access to your role/user might look like:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OnlyAllowSpecificPrincipal",
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::<ACCOUNT_ID>:role/mlflow-ec2-role",
          "arn:aws:iam::<ACCOUNT_ID>:user/mlflow-client"
        ]
      },
      "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::mlflow-artifacts-project",
        "arn:aws:s3:::mlflow-artifacts-project/*"
      ]
    }
  ]
}
```

---

## 5) Create and attach an **IAM Role** to the EC2 instance (server-side auth)

1. **IAM → Roles → Create role**
   - Trusted entity: **AWS service**
   - Use case: **EC2**
   - Attach policies (choose one):
     - *Testing*: **AmazonS3FullAccess**
     - *Scoped*: custom policy as in §2.3 but with the **role** as the principal
   - Name: `mlflow-ec2-role`

2. **Attach the role to your EC2 instance**
   - **EC2 → Instances → (select instance)**  
   - **Actions → Security → Modify IAM role**  
   - Choose `mlflow-ec2-role`

3. **Verify on the instance (SSH)**
   ```bash
   aws sts get-caller-identity
   aws s3 ls
   ```

> If the above commands work **without** any `AWS_PROFILE` or keys on the instance, the role is active.

---

## 6) Start MLflow server (reminder)

Use the **role** on EC2 to access S3 (no keys on the server):

```bash
# In a Python venv with compatible versions (MLflow 1.26.1, SQLAlchemy 1.4.36, etc.)
~/mlflow-venv/bin/mlflow server \
  -h 0.0.0.0 -p 5000 \
  --backend-store-uri "postgresql+psycopg2://DB_USER:ENC_PASS@DB_HOST:5432/DB_NAME?sslmode=require" \
  --default-artifact-root "s3://mlflow-artifacts-project"
```

- Client code (laptop) **does not** need `AWS_PROFILE` when the server handles S3:
  ```python
  os.environ.pop("AWS_PROFILE", None)
  ```
- To reach the server securely without exposing port 5000, use an **SSH tunnel**:
  ```bash
  ssh -i ~/Downloads/mlflow-key-pair.pem -L 5001:127.0.0.1:5000 ec2-user@<EC2_PUBLIC_DNS>
  # open http://localhost:5001
  ```

---

## 7) Troubleshooting

- **`ProfileNotFound: The config profile () could not be found`**
  - You set `AWS_PROFILE` to an **empty string** or an invalid name. Remove it:
    ```python
    os.environ.pop("AWS_PROFILE", None)
    ```
  - Or set to a valid profile you created:
    ```bash
    export AWS_PROFILE=mlflow-client
    ```

- **`AccessDenied` on S3**
  - Ensure the **EC2 role** has write permissions to the bucket (or your local profile if uploading directly).
  - Confirm **bucket region** and **client region** match (or set `AWS_DEFAULT_REGION`).

- **Cannot see S3 from EC2**
  - Verify the role is attached: `aws sts get-caller-identity` (should show an assumed-role ARN).
  - Instance must have outbound access (NAT/IGW).

- **HTTP to MLflow times out but `nc` succeeds**
  - Browser/network might block HTTP on high ports. Use SSH tunnel or set up NGINX on port 80 to proxy to 5000.

---

## 8) Minimal reference (copy/paste)

```bash
# Local (laptop) profile
aws configure --profile mlflow-client
aws sts get-caller-identity --profile mlflow-client
aws s3 ls --profile mlflow-client

# EC2: verify role-based access (no profile needed)
aws sts get-caller-identity
aws s3 ls

# MLflow server (on EC2)
~/mlflow-venv/bin/mlflow server -h 0.0.0.0 -p 5000 \
  --backend-store-uri "postgresql+psycopg2://USER:PASS@HOST:5432/DB?sslmode=require" \
  --default-artifact-root "s3://mlflow-artifacts-project"
```

---

**Done.** With this setup, your **EC2 server** uses an **IAM Role** to write MLflow artifacts to S3, while your **local machine** uses an **AWS profile** only when needed.
