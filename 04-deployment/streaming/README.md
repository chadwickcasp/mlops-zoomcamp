## Machine Learning for Streaming

* Scenario
* Creating the role 
* Create a Lambda function, test it
* Create a Kinesis stream
* Connect the function to the stream
* Send the records 

Links

* [Tutorial: Using Amazon Lambda with Amazon Kinesis](https://docs.amazonaws.cn/en_us/lambda/latest/dg/with-kinesis-example.html)

## Code snippets

### Sending data


```bash
KINESIS_STREAM_INPUT=ride_events
aws kinesis put-record \
    --stream-name ${KINESIS_STREAM_INPUT} \
    --partition-key 1 \
    --data "Hello, this is a test."
```
ChatGPT actually told me to do this because of AWS CLI v2

```bash
KINESIS_STREAM_INPUT=ride-events-1
aws kinesis put-record \
  --stream-name "$KINESIS_STREAM_INPUT" \
  --partition-key 1 \
  --cli-binary-format raw-in-base64-out \
  --data "Hello, this is a test.\n"
```

Decoding base64

```python
base64.b64decode(data_encoded).decode('utf-8')
```

Record example

```json
{
    "ride": {
        "PULocationID": 130,
        "DOLocationID": 205,
        "trip_distance": 3.66
    }, 
    "ride_id": 123
}
```

Sending this record using the edited version above

```bash
KINESIS_STREAM_INPUT=ride-events-1
aws kinesis put-record \
  --stream-name "$KINESIS_STREAM_INPUT" \
  --partition-key 1 \
  --cli-binary-format raw-in-base64-out \
  --data '{
        "ride": {
            "PULocationID": 130,
            "DOLocationID": 205,
            "trip_distance": 3.66
        }, 
        "ride_id": 156
    }'
```

### Test event


```json
{
    "Records": [
        {
            "kinesis": {
                "kinesisSchemaVersion": "1.0",
                "partitionKey": "1",
                "sequenceNumber": "49630081666084879290581185630324770398608704880802529282",
                "data": "ewogICAgICAgICJyaWRlIjogewogICAgICAgICAgICAiUFVMb2NhdGlvbklEIjogMTMwLAogICAgICAgICAgICAiRE9Mb2NhdGlvbklEIjogMjA1LAogICAgICAgICAgICAidHJpcF9kaXN0YW5jZSI6IDMuNjYKICAgICAgICB9LCAKICAgICAgICAicmlkZV9pZCI6IDI1NgogICAgfQ==",
                "approximateArrivalTimestamp": 1654161514.132
            },
            "eventSource": "aws:kinesis",
            "eventVersion": "1.0",
            "eventID": "shardId-000000000000:49630081666084879290581185630324770398608704880802529282",
            "eventName": "aws:kinesis:record",
            "invokeIdentityArn": "arn:aws:iam::XXXXXXXXX:role/lambda-kinesis-role",
            "awsRegion": "eu-west-1",
            "eventSourceARN": "arn:aws:kinesis:eu-west-1:XXXXXXXXX:stream/ride_events"
        }
    ]
}
```

### Reading from the stream

```bash
KINESIS_STREAM_OUTPUT='ride_predictions'
SHARD='shardId-000000000000'

SHARD_ITERATOR=$(aws kinesis \
    get-shard-iterator \
        --shard-id ${SHARD} \
        --shard-iterator-type TRIM_HORIZON \
        --stream-name ${KINESIS_STREAM_OUTPUT} \
        --query 'ShardIterator' \
)

RESULT=$(aws kinesis get-records --shard-iterator $SHARD_ITERATOR)

echo ${RESULT} | jq -r '.Records[0].Data' | base64 --decode
``` 

### Running the test
#### NOTE: Changed RUN_ID and other variables to the ones for my mlflow instance / AWS config from here on out

```bash
export PREDICTIONS_STREAM_NAME="ride_predictions"
export RUN_ID="ecfa50f261e64914817112759fbbfc48"
export TEST_RUN="True"

python test.py
```

### Putting everything to Docker

```bash
docker build -t stream-model-duration:v1 .

docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e RUN_ID="ecfa50f261e64914817112759fbbfc48" \
    -e TEST_RUN="True" \
    -e AWS_DEFAULT_REGION="us-west-1" \
    stream-model-duration:v1
```

URL for testing:

* http://localhost:8080/2015-03-31/functions/function/invocations



### Configuring AWS CLI to run in Docker

To use AWS CLI, you may need to set the env variables:

```bash
docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e RUN_ID="ecfa50f261e64914817112759fbbfc48" \
    -e TEST_RUN="True" \
    -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
    -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
    -e AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION}" \
    stream-model-duration:v1
```

Alternatively, you can mount the `.aws` folder with your credentials to the `.aws` folder in the container:

```bash
docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e RUN_ID="ecfa50f261e64914817112759fbbfc48" \
    -e TEST_RUN="True" \
    -v c:/Users/chadcasper/.aws:/root/.aws \
    stream-model-duration:v1
```

ALTERNATIVELY alternatively, you can mount the `.aws` folder with your credentials to the `.aws` folder in the container:

```bash
docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e RUN_ID="ecfa50f261e64914817112759fbbfc48" \
    -e TEST_RUN="True" \
    -e AWS_DEFAULT_REGION="us-west-1" \
    -v "${HOME}/.aws:/root/.aws:ro" \
    stream-model-duration:v1
```
The -v line mounts the ${HOME}/.aws directory as a \<v\>olume at /root/.aws in the container. The syntax ":ro" mounts it read-only for good security hygiene practice.

### Publishing Docker images

Creating an ECR repo

```bash
aws ecr create-repository --repository-name duration-model
```

Logging in

```bash
$(aws ecr get-login --no-include-email)
```
\
Apparently this was not the way to login to ECR. It is probably obsolete. This command worked instead:
```bash
aws ecr get-login-password --region us-west-1 | docker login --username AWS --password-stdin 413093438819.dkr.ecr.us-west-1.amazonaws.com
```


Pushing, using the URL I obtained: \
413093438819.dkr.ecr.us-west-1.amazonaws.com/duration-model

```bash
REMOTE_URI="413093438819.dkr.ecr.us-west-1.amazonaws.com/duration-model"
REMOTE_TAG="v1"
REMOTE_IMAGE=${REMOTE_URI}:${REMOTE_TAG}

LOCAL_IMAGE="stream-model-duration:v1"
docker tag ${LOCAL_IMAGE} ${REMOTE_IMAGE}
docker push ${REMOTE_IMAGE}
```
This didn't work because building the image locally resulted in a <b>linux/arm64</b> image, not a <b>linux/amd64</b> image. \
I got this built with the appropriate arch using the following commands:
```bash
docker buildx build \
  --platform linux/amd64 \
  -t stream-model-duration:v1-amd64 \
  --load \
  .
```
where the previous build didn't have the platform or load keywords (platform changes the arch, load gets it onto the local image store)

### Data In, Predictions Out

Now you can push to the Kinesis stream that you set up in AWS using the following CLI command (where ride-events is the name of the stream we setup in AWS):
```bash
KINESIS_STREAM_INPUT=ride-events

aws kinesis put-record \
  --stream-name "$KINESIS_STREAM_INPUT" \
  --partition-key 1 \
  --cli-binary-format raw-in-base64-out \
  --data '{
        "ride": {
            "PULocationID": 130,
            "DOLocationID": 205,
            "trip_distance": 3.66
        },
        "ride_id": 256
    }'
```

To read from the stream, execute:
```bash
KINESIS_STREAM_OUTPUT='ride_predictions'
SHARD='shardId-000000000000'

SHARD_ITERATOR=$(aws kinesis \
    get-shard-iterator \
        --shard-id ${SHARD} \
        --shard-iterator-type TRIM_HORIZON \
        --stream-name ${KINESIS_STREAM_OUTPUT} \
        --query 'ShardIterator' \
)

RESULT=$(aws kinesis get-records --shard-iterator $SHARD_ITERATOR)
```
And the following to format and decode the output JSON
```bash
echo ${RESULT} | jq -r '.Records[0].Data' | base64 --decode
```
Or the following to see only the formatted JSON:
```bash
echo ${RESULT} | jq 
```
