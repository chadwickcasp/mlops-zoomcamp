#!/usr/bin/env bash

set -e

# Use Docker Compose V2 plugin if available, else standalone docker-compose
if docker compose version &>/dev/null; then
  DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
  DOCKER_COMPOSE="docker-compose"
else
  echo "Neither 'docker compose' nor 'docker-compose' found. Install Docker Compose."
  exit 1
fi

if [[ -z "${GITHUB_ACTIONS}" ]]; then
  cd "$(dirname "$0")"
fi

if [ "${LOCAL_IMAGE_NAME}" == "" ]; then
    LOCAL_TAG=$(date +"%Y-%m-%d_%H-%M")
    export LOCAL_IMAGE_NAME="stream-model-duration:${LOCAL_TAG}"
    echo "LOCAL_IMAGE_NAME is not set, building the image with the default name: ${LOCAL_IMAGE_NAME}"
    docker build -t ${LOCAL_IMAGE_NAME} ..
else
    echo "LOCAL_IMAGE_NAME is set to: ${LOCAL_IMAGE_NAME}"
    echo "No need to build the image"
fi

export PREDICTIONS_STREAM_NAME="ride_predictions"

# Pass PREDICTIONS_STREAM_NAME explicitly so docker-compose variable substitution works (CI runs script via pipe)
PREDICTIONS_STREAM_NAME="${PREDICTIONS_STREAM_NAME:-ride_predictions}" ${DOCKER_COMPOSE} up -d

sleep 5

# Delete stream if it exists (ignore errors if it doesn't)
aws --endpoint-url=http://localhost:4566 \
    kinesis delete-stream \
    --stream-name ${PREDICTIONS_STREAM_NAME} \
    2>/dev/null || true

# Wait a moment for deletion to complete
sleep 2

# Create the stream
echo "Creating stream..."
aws --endpoint-url=http://localhost:4566 \
    kinesis create-stream \
    --stream-name ${PREDICTIONS_STREAM_NAME} \
    --shard-count 1

pipenv run python test_docker.py

ERROR_CODE=$?

if [ $ERROR_CODE -ne 0 ]; then
    ${DOCKER_COMPOSE} logs
    ${DOCKER_COMPOSE} down
    exit ${ERROR_CODE}
fi

pipenv run python test_kinesis.py

ERROR_CODE=$?

if [ $ERROR_CODE -ne 0 ]; then
    ${DOCKER_COMPOSE} logs
    ${DOCKER_COMPOSE} down
    exit ${ERROR_CODE}
fi

${DOCKER_COMPOSE} down

