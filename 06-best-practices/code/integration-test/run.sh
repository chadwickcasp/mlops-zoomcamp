#!/usr/bin/env bash

set -e

if [[ -z "${GITHUB_ACTIONS}" ]]; then
    cd "$(dirname "$0")"

if [ "${LOCAL_IMAGE_NAME}" == "" ]; then
    LOCAL_TAG=$(date +"%Y-%m-%d_%H-%M")
    export LOCAL_IMAGE_NAME="stream-model-duration:${LOCAL_TAG}"
    echo "LOCAL_IMAGE_NAME is not set, building the image with the default name: ${LOCAL_IMAGE_NAME}"
    docker build -t ${LOCAL_IMAGE_NAME} ..
else
    echo "LOCAL_IMAGE_NAME is set to: ${LOCAL_IMAGE_NAME}"
    echo "No need to build the image"
fi

PREDICTIONS_STREAM_NAME="ride_predictions"

docker-compose up -d

sleep 1

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
    docker-compose logs
    docker-compose down
    exit ${ERROR_CODE}
fi

pipenv run python test_kinesis.py

ERROR_CODE=$?

if [ $ERROR_CODE -ne 0 ]; then
    docker-compose logs
    docker-compose down
    exit ${ERROR_CODE}
fi

docker-compose down
