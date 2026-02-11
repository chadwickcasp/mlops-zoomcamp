# GCP + Computer Vision Capstone: Migration Guide

This document outlines how the current MLOps Zoomcamp project (AWS + tabular taxi duration prediction) would differ if you built the capstone using **GCP** and **image data with a computer vision model**. It serves as a roadmap for adapting the learning from this course to a vision-based capstone.

> **Framework**: This guide uses **PyTorch** (with `torchvision`) for model training and inference. All code examples and references are PyTorch equivalents.

---

## Table of Contents

1. [Current Architecture Overview](#1-current-architecture-overview)
2. [AWS → GCP Service Mapping](#2-aws--gcp-service-mapping)
3. [Tabular → Image / Computer Vision Differences](#3-tabular--image--computer-vision-differences)
4. [Section-by-Section Migration](#4-section-by-section-migration)
5. [New Considerations for Computer Vision](#5-new-considerations-for-computer-vision)
6. [Recommended Capstone Architecture (GCP + CV)](#6-recommended-capstone-architecture-gcp--cv)

---

## 1. Current Architecture Overview

The MLOps Zoomcamp project uses:

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Data** | Parquet (NYC taxi trip records) | Tabular features: PULocationID, DOLocationID, trip_distance |
| **Storage** | AWS S3 | Model artifacts, batch outputs, MLflow artifacts |
| **Compute** | AWS Lambda | Streaming inference (Kinesis → Lambda → predictions) |
| **Streaming** | Kinesis | Event stream for ride events |
| **Container Registry** | ECR | Docker images for Lambda |
| **Orchestration** | Prefect | Scheduled training, batch jobs |
| **Experiment Tracking** | MLflow | Experiments, model registry |
| **Monitoring** | Evidently, MongoDB, Prometheus/Grafana | Drift, predictions, metrics |
| **IaC** | Terraform | S3, Lambda, Kinesis, IAM |

---

## 2. AWS → GCP Service Mapping

| AWS Service | GCP Equivalent | Notes |
|-------------|----------------|-------|
| **S3** | **Cloud Storage (GCS)** | Same object storage paradigm. Use `gs://bucket/path` instead of `s3://bucket/path`. Python: `google-cloud-storage` or `gcsfs`. |
| **Lambda** | **Cloud Functions** | Serverless, event-driven. Similar cold-start behavior. Alternative: **Cloud Run** (better for larger containers, longer requests, or GPU). |
| **Kinesis** | **Pub/Sub** | Message queue / event stream. Different API (publish/subscribe vs. shards). For ordered processing: **Dataflow** (Apache Beam). |
| **ECR** | **Artifact Registry** | Container images. Similar to ECR. |
| **EC2** | **Compute Engine (GCE)** | VMs for MLflow server, long-running jobs. |
| **RDS PostgreSQL** | **Cloud SQL** | Managed PostgreSQL for MLflow backend. |
| **IAM** | **IAM / Service Accounts** | GCP uses service accounts (JSON keys) instead of access keys. |
| **Terraform** | **Terraform** | Same tool; swap `aws` provider for `google` provider. |
| **LocalStack** | **LocalStack** or **GCP emulators** | LocalStack supports S3 only; for GCP locally use `fake-gcs-server` or `fsouza/fake-gcs-server` for GCS. |

### Code Changes for GCP

| Current (AWS) | GCP Equivalent |
|---------------|----------------|
| `boto3.client('s3')` | `google.cloud.storage.Client()` |
| `boto3.client('kinesis')` | `google.cloud.pubsub_v1.Publisher/SubscriberClient()` |
| `s3://bucket/key` | `gs://bucket/key` |
| `mlflow.log_artifact()` with S3 backend | Same MLflow API; set `--default-artifact-root gs://bucket` |
| Lambda `lambda_handler(event, context)` | Cloud Function `def entrypoint(request)` or `def entrypoint(event, context)` |
| ECR image URI | `REGION-docker.pkg.dev/PROJECT/REPO/IMAGE:TAG` |

---

## 3. Tabular → Image / Computer Vision Differences

### 3.1 Data Format & Storage

| Aspect | Tabular (Current) | Image / Computer Vision |
|--------|-------------------|--------------------------|
| **Format** | Parquet (columnar, compressed) | JPEG, PNG, TIFF; often in folders or `ImageFolder`-style dirs |
| **Size** | KB–MB per file | KB–MB per image; datasets often 10s–100s of GB |
| **Structure** | Rows × columns | Pixels × channels; metadata (labels) separate |
| **Loading** | `pd.read_parquet()` | PIL, OpenCV, `torchvision.datasets.ImageFolder`, or `torchvision.io.read_image` |
| **Batching** | DataFrame chunks | `DataLoader` with image transforms |

### 3.2 Preprocessing

| Tabular | Image |
|---------|-------|
| `DictVectorizer` for categoricals | Resize, normalize, augmentation (flip, crop, color jitter) |
| Fill missing, cast types | Channel normalization (ImageNet mean/std) |
| `df[categorical].astype(str)` | `torchvision.transforms` (Resize, Normalize) or custom preprocessing |

### 3.3 Model Architecture

| Tabular | Image |
|---------|-------|
| LinearRegression, RandomForest | CNN (ResNet, EfficientNet, ViT) |
| scikit-learn | PyTorch, torchvision |
| Small model files (KB) | Large model files (MB–GB) |
| Fast inference (~ms) | Slower inference (ms–100s ms depending on size) |

### 3.4 Inference Payload

| Tabular | Image |
|---------|-------|
| JSON: `{"PULocationID": 10, "DOLocationID": 50, "trip_distance": 40}` | Base64-encoded image or GCS URL |
| Payload size: ~100 bytes | Payload size: 100KB–5MB |
| **Lambda limit: 6MB** | Images can exceed this; need Cloud Run or different design |

### 3.5 Batch vs. Streaming

| Tabular | Image |
|---------|-------|
| One parquet file = many rows | One request = one image (or small batch) |
| Batch: read parquet → predict all → write parquet | Batch: iterate over images, predict, write results CSV/JSON |
| Streaming: one ride event per Kinesis record | Streaming: one image per Pub/Sub message (or URL) |

### 3.6 Experiment Tracking (MLflow)

| Tabular | Image |
|---------|-------|
| Log params, metrics, small artifacts | Same; artifacts larger (model checkpoints, sample images) |
| Model: pickle/sklearn | Model: `mlflow.pytorch.log_model()` |
| Artifact root: S3/GCS | Same; ensure GCS quota for large runs |

### 3.7 Monitoring & Drift

| Tabular | Image |
|---------|-------|
| Evidently: feature drift (Jensen-Shannon, etc.) | Evidently: supports image drift (e.g., Image Histogram) |
| Metrics: RMSE, MAE | Metrics: Accuracy, F1, IoU, mAP (depending on task) |
| Target drift: duration distribution | Target drift: class distribution, confidence scores |
| Reference data: parquet | Reference data: image dataset or embeddings |

---

## 4. Section-by-Section Migration

### 4.1 Introduction (01-intro)

| Current | GCP + CV |
|---------|----------|
| `read_dataframe()`, `DictVectorizer`, `LinearRegression` | `torchvision.datasets.ImageFolder` + `DataLoader`, `torchvision.models.resnet50` or EfficientNet |
| Parquet files in `data/` | Images in `data/train/`, `data/val/` by class |
| Mean squared error | Cross-entropy, accuracy, or task-specific metric |

### 4.2 Experiment Tracking (02-experiment-tracking)

| Current | GCP + CV |
|---------|----------|
| MLflow on EC2, S3 artifacts | MLflow on GCE or Cloud Run, **GCS** artifacts |
| `--default-artifact-root s3://bucket` | `--default-artifact-root gs://bucket` |
| Log sklearn model | `mlflow.pytorch.log_model()` |
| Autolog for sklearn | `mlflow.pytorch.autolog()` |

### 4.3 Orchestration (03-orchestration)

| Current | GCP + CV |
|---------|----------|
| Prefect flow: download parquet, train, save model | Same flow; download images (or read from GCS), train CNN, save model |
| `get_paths(date)` → parquet paths | `get_paths(date)` → GCS paths or local image directories |
| Model: `model-{date}.bin` | Model: `model-{date}.pt` or `model-{date}.pth` (PyTorch state_dict or full model) |

### 4.4 Deployment (04-deployment)

| Current | GCP + CV |
|---------|----------|
| Batch: read parquet, predict, write parquet | Batch: read images from GCS, predict, write predictions to GCS |
| Docker: `agrigorev/zoomcamp-model` | Docker: PyTorch base image (`pytorch/pytorch`) + your model |
| S3 upload for outputs | GCS upload for outputs |
| Streaming: Lambda + Kinesis | **Cloud Run** + Pub/Sub (Lambda payload limits too small for images) |

### 4.5 Monitoring (05-monitoring)

| Current | GCP + CV |
|---------|----------|
| Evidently: tabular drift | Evidently: **Image Data Drift** (image histograms, embeddings) |
| MongoDB for predictions | Same; store image path/URL, prediction, confidence |
| Prometheus + Grafana | Same; add image-specific metrics (inference latency, GPU usage) |

### 4.6 Best Practices (06-best-practices)

| Current | GCP + CV |
|---------|----------|
| Terraform: AWS (S3, Lambda, Kinesis, ECR) | Terraform: **GCP** (GCS, Cloud Run, Pub/Sub, Artifact Registry) |
| LocalStack for S3 | `fsouza/fake-gcs-server` for GCS |
| Integration test: parquet → S3 → batch | Integration test: images → GCS → batch |
| CI: build Docker, push to ECR | CI: build Docker, push to Artifact Registry |

---

## 5. New Considerations for Computer Vision

### 5.1 Compute Requirements

- **Training**: GPUs (e.g., T4, A100 on GCP) for reasonable training time.
- **Inference**: Cloud Run with GPU optional; CPU often sufficient for smaller models (e.g., `torchvision.models.mobilenet_v3_small`).

### 5.2 Data Versioning

- Tabular: DVC can version parquet files.
- Images: DVC works; alternatives: **Vertex AI Datasets**, **Pachyderm**, or GCS with manifest files.

### 5.3 Model Size & Cold Start

- Lambda: 250MB deployment package limit; often too small for large CNNs.
- **Cloud Run**: No hard limit; scale-to-zero; cold start can be several seconds for large models.
- Consider **Vertex AI Endpoints** for high-throughput, managed inference.

### 5.4 Image-Specific Drift

- **Input drift**: Image resolution, lighting, camera model changes.
- **Semantic drift**: New object types, backgrounds.
- Tools: Evidently image drift, or custom embedding-based drift (e.g., cosine distance in feature space).

### 5.5 Augmentation & Reproducibility

- Image augmentation (flip, rotate, color) must be reproducible or logged for experiments.
- MLflow can log augmentation config as params.

---

## 6. Recommended Capstone Architecture (GCP + CV)

### High-Level Diagram

```
[Image Dataset] → GCS (raw) / Vertex AI Dataset
       ↓
[Prefect Flow] → train on GCE (GPU) or Vertex AI Training
       ↓
[MLflow] → GCS artifacts, Cloud SQL backend
       ↓
[Model Registry] → promote best model
       ↓
[Cloud Run] ← Pub/Sub (or HTTP) for real-time inference
       ↓
[BigQuery / Firestore] for predictions + Evidently monitoring
```

### Suggested Tech Stack

| Component | Recommendation |
|-----------|----------------|
| **Data storage** | GCS for images; optional Vertex AI Datasets |
| **Experiment tracking** | MLflow (GCE or Cloud Run) + GCS |
| **Orchestration** | Prefect (same as course) or Vertex AI Pipelines |
| **Training** | GCE with GPU, or Vertex AI Training |
| **Model registry** | MLflow or Vertex AI Model Registry |
| **Deployment** | Cloud Run (HTTP) or Vertex AI Endpoints |
| **Streaming** | Pub/Sub (if needed) |
| **Monitoring** | Evidently (image drift) + Cloud Monitoring / Prometheus |
| **IaC** | Terraform with `google` provider |

### Example Datasets for CV Capstone

- **Classification**: CIFAR-10, Food-101, PlantVillage, skin lesion (ISIC)
- **Detection**: COCO subset, custom labeled images
- **Segmentation**: Cityscapes subset, medical images

### Terraform Skeleton for GCP

```hcl
terraform {
  backend "gcs" {
    bucket = "your-tf-state-bucket"
    prefix = "mlops-cv-capstone"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "models" { ... }
resource "google_storage_bucket" "data" { ... }
resource "google_artifact_registry_repository" "repos" { ... }
resource "google_cloud_run_service" "inference" { ... }
resource "google_pubsub_topic" "inference" { ... }
```

---

## Summary

| Dimension | Current (AWS + Tabular) | Capstone (GCP + CV) |
|-----------|------------------------|----------------------|
| **Cloud** | AWS (S3, Lambda, Kinesis, ECR) | GCP (GCS, Cloud Run, Pub/Sub, Artifact Registry) |
| **Data** | Parquet, DictVectorizer | Images, CNN preprocessing |
| **Model** | sklearn (LinearRegression, RF) | PyTorch CNN (torchvision) |
| **Inference** | Lambda (small payloads) | Cloud Run (larger payloads, optional GPU) |
| **Streaming** | Kinesis | Pub/Sub |
| **Drift** | Evidently tabular | Evidently image + embeddings |
| **IaC** | Terraform (aws) | Terraform (google) |

The core MLOps patterns (experiment tracking, orchestration, deployment, monitoring, IaC) remain the same; the main differences are in data handling, model type, and the specific cloud services used.
