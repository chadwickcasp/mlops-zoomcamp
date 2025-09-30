# MLflow on AWS (EC2 + PostgreSQL + S3) — Setup Guide

This guide captures the steps and versions we used to run **MLflow 1.26.x** on an EC2 instance with **PostgreSQL** as the backend store and **S3** for artifacts. It’s designed for Amazon Linux 2 (adjust apt/yum commands if you use a different distro).

---

## 0) Prerequisites & Topology

- **EC2 instance** with a public IPv4 in a **public subnet** (route to an Internet Gateway).
- **Security Groups (SGs):**
  - **Instance SG**: allow **SSH (22)** from your IP. Optionally **HTTP (80)** if using NGINX, or **Custom TCP 5000** from your IP if accessing the MLflow port directly.
  - **RDS SG** (if using Amazon RDS): allow **PostgreSQL 5432 from the Instance SG** (by SG ID, not 0.0.0.0/0).
- **S3 bucket** for artifacts, and AWS credentials for the instance (IAM role preferred).
- **PostgreSQL** reachable from EC2 (RDS or self-managed).

> **Tip:** For remote browser access without opening port 5000, use an **SSH tunnel** or an **NGINX reverse proxy on port 80** (see §7).

---

## 1) SSH into the instance

```bash
ssh -i ~/Downloads/mlflow-key-pair.pem ec2-user@<EC2_PUBLIC_DNS>
```

> Replace `ec2-user` with the correct user for your AMI (`ubuntu` on Ubuntu).

---

## 2) Create a dedicated Python virtualenv

```bash
python3 -m venv ~/mlflow-venv
source ~/mlflow-venv/bin/activate
```

---

## 3) Pin build tools and install period-correct package versions

These versions match the 2022-era MLflow stack and avoid SQLAlchemy 2.x incompatibilities.

```bash
python -m pip install -U "pip==22.0.4" "setuptools==62.3.2" "wheel==0.37.1"

# Remove newer DB libs if present
python -m pip uninstall -y sqlalchemy alembic greenlet

# Install the compatible set
python -m pip install \
  "mlflow==1.26.1" \
  "SQLAlchemy==1.4.36" \
  "alembic==1.7.7" \
  "greenlet==1.1.2" \
  "psycopg2-binary==2.9.3" \
  "protobuf==3.20.3" "grpcio==1.46.3" "googleapis-common-protos==1.56.0" \
  "boto3==1.21.21"
```

Block user-site packages (to prevent `~/.local` from leaking newer libs):
```bash
export PYTHONNOUSERSITE=1
```

---

## 4) Verify versions

```bash
python - <<'PY'
import mlflow, sqlalchemy, alembic, google.protobuf as pb
print("mlflow", mlflow.__version__)
print("SQLAlchemy", sqlalchemy.__version__)
print("alembic", alembic.__version__)
print("protobuf", pb.__version__)
PY
```
Expected:
```
mlflow 1.26.1
SQLAlchemy 1.4.36
alembic 1.7.7
protobuf 3.20.3
```

---

## 5) Launch MLflow server

Build a **Postgres** SQLAlchemy URI (URL-encode special chars in your password) and choose your S3 bucket:

```bash
DB_HOST="your-db-endpoint.rds.amazonaws.com"
DB_NAME="mlflow"
DB_USER="mlflow"
DB_PASS_ENC="<URL-encoded-password>"   # use python's urllib.parse.quote_plus locally if needed

ARTIFACT_ROOT="s3://your-mlflow-bucket"

~/mlflow-venv/bin/mlflow server \
  -h 0.0.0.0 -p 5000 \
  --backend-store-uri "postgresql+psycopg2://${DB_USER}:${DB_PASS_ENC}@${DB_HOST}:5432/${DB_NAME}?sslmode=require" \
  --default-artifact-root "${ARTIFACT_ROOT}"
```

Health check on the instance:
```bash
curl -I http://127.0.0.1:5000/
```

---

## 6) Access options

### A) SSH tunnel (no SG changes for port 5000)

On your laptop:
```bash
ssh -i ~/Downloads/mlflow-key-pair.pem \
    -L 5001:127.0.0.1:5000 \
    ec2-user@<EC2_PUBLIC_DNS>
# open http://localhost:5001
```

### B) Reverse proxy with NGINX on port 80 (browser-friendly)

```bash
sudo yum install -y nginx   # (apt-get on Ubuntu/Debian)
sudo systemctl enable --now nginx

sudo tee /etc/nginx/conf.d/mlflow.conf >/dev/null <<'NGINX'
server {
  listen 80;
  server_name _;

  proxy_read_timeout 600s;
  proxy_connect_timeout 60s;
  proxy_send_timeout 600s;

  location / {
    proxy_pass         http://127.0.0.1:5000;
    proxy_http_version 1.1;
    proxy_set_header   Host $host;
    proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_set_header   Upgrade $http_upgrade;
    proxy_set_header   Connection "upgrade";
  }
}
NGINX

sudo nginx -t && sudo systemctl reload nginx
```
Now browse: `http://<EC2_PUBLIC_DNS>/`

> For HTTPS, front with an **ALB + ACM** cert, or use **certbot** on the instance.

---

## 7) Run MLflow as a service (systemd)

Create `/etc/systemd/system/mlflow.service`:

```ini
[Unit]
Description=MLflow Server
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user
Environment=PYTHONNOUSERSITE=1
ExecStart=/home/ec2-user/mlflow-venv/bin/mlflow server -h 0.0.0.0 -p 5000 \
          --backend-store-uri postgresql+psycopg2://${DB_USER}:${DB_PASS_ENC}@${DB_HOST}:5432/${DB_NAME}?sslmode=require \
          --default-artifact-root ${ARTIFACT_ROOT}
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable & start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mlflow
sudo systemctl status mlflow
```

Stop/Start:
```bash
sudo systemctl stop mlflow
sudo systemctl start mlflow
```

---

## 8) Troubleshooting

**Port already in use**
```bash
ss -ltnp | grep ':5000'
ps -ef | egrep 'mlflow server|gunicorn' | grep -v grep | awk '{print $2}' | xargs -r kill
```

**UI shows `BAD_REQUEST: "whens" argument to case()`**
- You’re picking up **SQLAlchemy 2.x**. Ensure the server process uses **SQLAlchemy 1.4.36** (see §3) and `PYTHONNOUSERSITE=1` so `~/.local` doesn’t leak newer packages.

**DB migration / `Connection object has no attribute 'connect'`**
- Same root cause: **Alembic/SQLAlchemy too new**. Pin to **Alembic 1.7.7** and **SQLAlchemy 1.4.36**.

**Can’t connect from browser on :5000** but `nc` works
- Corporate/home networks often block HTTP on high ports. Use **SSH tunnel** or **NGINX on port 80**.

**RDS connectivity issues**
- Verify with `psql` from EC2:
  ```bash
  psql "host=${DB_HOST} port=5432 dbname=${DB_NAME} user=${DB_USER} password=<raw-pass> sslmode=require" -c '\dt'
  ```
- Fix SGs: RDS SG must allow **5432 from the Instance SG**.

**S3 permissions**
- Prefer an **instance IAM role** with `s3:PutObject, s3:GetObject, s3:ListBucket` on your bucket.
- Optionally set `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` env vars.

---

## 9) Operational tips

- Logs when run via systemd:
  ```bash
  journalctl -u mlflow -f
  ```
- Gunicorn tuning (optional):
  ```bash
  ~/mlflow-venv/bin/mlflow server ... --gunicorn-opts="--timeout 120 --workers 2 --threads 4"
  ```
- Keep security tight: avoid exposing port 5000 to the world; prefer 80/443 via NGINX/ALB.

---

## 10) Quick reference (copy/paste)

```bash
# create venv
python3 -m venv ~/mlflow-venv
source ~/mlflow-venv/bin/activate

# pin tools & install versions
pip install -U "pip==22.0.4" "setuptools==62.3.2" "wheel==0.37.1"
pip uninstall -y sqlalchemy alembic greenlet
pip install "mlflow==1.26.1" "SQLAlchemy==1.4.36" "alembic==1.7.7" "greenlet==1.1.2" \
            "protobuf==3.20.3" "grpcio==1.46.3" "googleapis-common-protos==1.56.0" \
            "psycopg2-binary==2.9.3" "boto3==1.21.21"
export PYTHONNOUSERSITE=1

# run server
DB_HOST=your-db.rds.amazonaws.com
DB_NAME=mlflow
DB_USER=mlflow
DB_PASS_ENC=<url-encoded-pass>
ARTIFACT_ROOT=s3://your-bucket

~/mlflow-venv/bin/mlflow server -h 0.0.0.0 -p 5000 \
  --backend-store-uri "postgresql+psycopg2://${DB_USER}:${DB_PASS_ENC}@${DB_HOST}:5432/${DB_NAME}?sslmode=require" \
  --default-artifact-root "${ARTIFACT_ROOT}"
```

---

**That’s it!** This setup has been validated to avoid SQLAlchemy 2.x and protobuf 4.x pitfalls with MLflow 1.26.x, and keeps access secure via SSH tunneling or NGINX on port 80.
