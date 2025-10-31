#!/usr/bin/env bash
set -euo pipefail

# === Prefect 2.0b5 full install into an EXISTING MLflow venv (Amazon Linux) ===
# Strategy: keep your MLflow-era AWS pins (boto3 1.21.21 / botocore 1.24.46)
# and align the async S3 stack to them (aiobotocore 2.3.x, s3fs 2022.5.0).
#
# Usage:
#   # (optionally) point to your venv
#   # VENV=/home/ec2-user/mlflow-venv  bash install-prefect-2.0b5-into-mlflow-venv.sh
#   # otherwise defaults to ~/.venvs/mlflow-venv
#
# After install:
#   source <venv>/bin/activate
#   prefect version && prefect orion start --host 127.0.0.1 --port 4200

VENV_DEFAULT="${HOME}/.venvs/mlflow-venv"
VENV_PATH="${VENV:-$VENV_DEFAULT}"

# 0) Activate venv
if [ -z "${VIRTUAL_ENV:-}" ]; then
  if [ -d "$VENV_PATH" ]; then
    echo "Activating venv: $VENV_PATH"
    # shellcheck disable=SC1090
    source "$VENV_PATH/bin/activate"
  else
    echo "❌ No active venv and $VENV_PATH not found."
    echo "   Activate your MLflow venv or set VENV=/path/to/venv and re-run."
    exit 1
  fi
else
  echo "Using active venv: $VIRTUAL_ENV"
fi

echo "Python: $(python -V)"
pip --version || true
pip freeze > pip-freeze-before-prefect.txt || true

# 1) Toolchain pins (May 2022)
python -m pip install --upgrade "pip==22.0.4" "setuptools==62.3.2" "wheel==0.37.1"

# 2) Pre-install low-level compiled wheels (helps on AL2/AL2023)
# Try wheels first; if unavailable, fall back to source build (requires devel headers)
python -m pip install --only-binary=:all: \
  "cffi==1.15.0" "cryptography==37.0.2" "pyopenssl==22.0.0" "google-crc32c==1.3.0" || \
python -m pip install \
  "cffi==1.15.0" "cryptography==37.0.2" "pyopenssl==22.0.0" "google-crc32c==1.3.0"

# 3) Final pinned requirements (Option A alignment)
REQ_FILE="$(mktemp /tmp/prefect20b5-optA-reqs.XXXXXX.txt)"
cat > "$REQ_FILE" <<'REQ'
# ---------- Prefect core ----------
prefect==2.0b5
pydantic==1.9.1
typing_extensions==4.2.0
typer==0.6.1
shellingham==1.4.0
rich==12.4.4
pygments==2.12.0
commonmark==0.9.1
coolname==1.1.0
readchar==4.0.3
python-slugify==6.1.2
text-unidecode==1.3
croniter==1.3.1
pendulum==2.1.2
pytzdata==2020.1
python-dateutil==2.8.2
toml==0.10.2
aiofiles==0.8.0

# ---------- HTTP / async stack ----------
httpx==0.22.0
httpcore==0.14.7
sniffio==1.2.0
h11==0.12.0
rfc3986[idna2008]==1.5.0
idna==3.3
certifi==2021.10.8
charset-normalizer==2.0.12
anyio==3.6.1

# ---------- API / web server ----------
fastapi==0.78.0
starlette==0.19.1
uvicorn==0.17.6
asgi_lifespan==1.0.1
asgiref==3.5.2

# ---------- SQLite / ORM ----------
aiosqlite==0.17.0
sqlalchemy==1.4.36
alembic==1.7.7
mako==1.2.0
greenlet==1.1.2
sqlite-utils==3.27
click-default-group-wheel==1.2.2
sqlite-fts4==1.0.3

# ---------- Filesystem / Cloud FS ----------
fsspec==2022.3.0
# align s3fs to botocore 1.24.x line (works with aiobotocore 2.3.x)
s3fs==2022.5.0
gcsfs==2022.3.0
decorator==5.1.1
google-auth-oauthlib==0.5.1

# ---------- AWS async + SDK (Option A pins) ----------
# Keep course pins; align async layer to them
boto3==1.21.21
botocore==1.24.46
s3transfer==0.5.2
jmespath==1.0.0
aiobotocore==2.3.4
aiohttp==3.8.1
aioitertools==0.10.0
aiosignal==1.2.0
multidict==6.0.2
yarl==1.7.2
async-timeout==4.0.2
frozenlist==1.3.0
wrapt==1.14.1

# ---------- Google Cloud ----------
google-cloud-storage==2.3.0
google-cloud-core==2.3.0
google-resumable-media==2.3.2
google-api-core==2.7.1
google-auth==2.6.6
cachetools==5.1.0
rsa==4.8
pyasn1==0.4.8
pyasn1-modules==0.2.8
googleapis-common-protos==1.56.0
protobuf==3.20.1
grpcio==1.46.3
six==1.16.0
google-crc32c==1.3.0

# ---------- Azure ----------
azure-storage-blob==12.9.0
azure-core==1.24.1
msrest==0.6.21
isodate==0.6.1

# ---------- Requests / OAuth ----------
requests==2.27.1
urllib3==1.26.9
requests-oauthlib==1.3.1
oauthlib==3.2.0

# ---------- Misc small runtime helpers ----------
packaging==21.3
click==8.1.2
tqdm==4.64.0
colorama==0.4.4
importlib-metadata==4.11.4
zipp==3.8.0
attrs==21.4.0
REQ

python -m pip install --no-deps -r "$REQ_FILE"

# 4) Ensure final network/AWS stack is exactly aligned (defensive re-pin)
python -m pip install --force-reinstall \
  "urllib3==1.26.9" \
  "requests==2.27.1" \
  "boto3==1.21.21" \
  "botocore==1.24.46" \
  "s3transfer==0.5.2" \
  "jmespath==1.0.0"

# 5) Integrity check & smoke tests
pip check || true

python - <<'PY'
import prefect, fastapi, httpx
import fsspec, s3fs, gcsfs
import boto3, botocore, aiobotocore, jmespath
import aiohttp, aioitertools, aiosignal, yarl, multidict, async_timeout, frozenlist
from google.cloud import storage as gcs_storage
import azure.core, azure.storage.blob
import aiosqlite, sqlalchemy, alembic, mako, greenlet
import cryptography, cffi, requests, urllib3, attrs
print("✅ Prefect:", prefect.__version__)
print("FastAPI:", fastapi.__version__, "httpx:", httpx.__version__)
print("FS  :", "fsspec", fsspec.__version__, "s3fs", s3fs.__version__, "gcsfs", gcsfs.__version__)
print("AWS :", "boto3", boto3.__version__, "botocore", botocore.__version__, "aiobotocore", aiobotocore.__version__)
print("AIO :", "aiohttp", aiohttp.__version__, "aioitertools", aioitertools.__version__, "aiosignal", aiosignal.__version__)
print("AIO2:", "yarl", yarl.__version__, "multidict", multidict.__version__, "async-timeout", async_timeout.__version__, "frozenlist", frozenlist.__version__)
print("GCP :", "gcs", gcs_storage.__version__)
print("AZ  :", "azure-core", azure.core.__version__, "azure-blob", azure.storage.blob.__version__)
print("DB  :", "aiosqlite", aiosqlite.__version__, "sqlalchemy", sqlalchemy.__version__, "alembic", alembic.__version__, "mako", mako.__version__, "greenlet", greenlet.__version__)
print("Net :", "requests", requests.__version__, "urllib3", urllib3.__version__)
print("Sec :", "cryptography", cryptography.__version__, "cffi", cffi.__version__)
print("Misc:", "attrs", attrs.__version__)
PY

echo "✅ Done. Prefect 2.0b5 + complete deps installed into: ${VIRTUAL_ENV:-$VENV_PATH}"
echo "   Run: prefect version && prefect orion start --host 127.0.0.1 --port 4200"
