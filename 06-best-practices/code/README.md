
```bash
docker build -t stream-model-duration:v2 .
```

Zoomcamp says to do this to test the container:
```bash
docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e RUN_ID="ecfa50f261e64914817112759fbbfc48" \
    -e TEST_RUN="True" \
    -e AWS_DEFAULT_REGION="us-west-1" \
    stream-model-duration:v2
```

I actually have to do this:
```bash
docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e RUN_ID="ecfa50f261e64914817112759fbbfc48" \
    -e TEST_RUN="True" \
    -e AWS_DEFAULT_REGION="us-west-1" \
    -v "${HOME}/.aws:/root/.aws:ro" \
    stream-model-duration:v2
```

Then to run the container with integration tests:
```bash
docker run -it --rm \
    -p 8080:8080 \
    -e PREDICTIONS_STREAM_NAME="ride_predictions" \
    -e RUN_ID="ecfa50f261e64914817112759fbbfc48" \
    -e MODEL_LOCATION="/app/model" \
    -e TEST_RUN="True" \
    -e AWS_DEFAULT_REGION="us-west-1" \
    -v "${HOME}/.aws:/root/.aws:ro" \
    -v "$(pwd)/integration-test/model:/app/model:ro" \
    stream-model-duration:v2
```

After editing the ```docker-compose.yaml``` file so that it sets up a local AWS stack with kinesis via localstack, you can query the local kinesis service with:
```bash
aws --endpoint-url=http://localhost:4566 kinesis lis
t-streams
```

To create a stream, execute:
```bash
aws --endpoint-url=http://localhost:4566 \
    kinesis create-stream \
    --stream-name ride_predictions \
    --shard-count 1
```

Just as we read from the stream in 04-deployment, we can read from it again:
```bash
PREDICTIONS_STREAM_NAME='ride_predictions'
SHARD='shardId-000000000000'

SHARD_ITERATOR=$(aws --endpoint-url=http://localhost:4566 \
    kinesis get-shard-iterator \
        --shard-id ${SHARD} \
        --shard-iterator-type TRIM_HORIZON \
        --stream-name ${PREDICTIONS_STREAM_NAME} \
        --query 'ShardIterator' \
        --output text)
```

Running the following command on that output:
```bash
aws --endpoint-url=http://localhost:4566 \
    kinesis get-records \
        --shard-iterator ${SHARD_ITERATOR}
```

Gives expected:
```bash
{
    "Records": [
        {
            "SequenceNumber": "49671222862245240340665719458789621747952841301380038658",
            "ApproximateArrivalTimestamp": "2026-01-26T13:32:45-08:00",
            "Data": "eyJtb2RlbCI6ICJyaWRlX2R1cmF0aW9uX3ByZWRpY3Rpb25fbW9kZWwiLCAidmVyc2lvbiI6ICJUZXN0MTIzIiwgInByZWRpY3Rpb24iOiB7InJpZGVfZHVyYXRpb24iOiAxOC4xNjg5NDU3MjY0MDUzMywgInJpZGVfaWQiOiAxNTZ9fQ==",
            "PartitionKey": "156",
            "EncryptionType": "NONE"
        }
    ],
    "NextShardIterator": "AAAAAAAAAAECch4JIsq0989Bma5Tmt0yDfi33kpVaQHUwZp0Kg38GtGTJ+rd/5rEXaw1sa/Pu7xHS8CQBTYJBD6Lv3FKiYVz1xha/HQW7L3ijYJYKQOWEI5OHTuqRWANqaykSOEu/h9QUDi/n7CAwsqD0h//ogb7wsmgkFFK9grm4wowAyunc1C5ib99A7YZcwiwPaSmET0w1W7/VBYe1pli3HxX8KQK",
    "MillisBehindLatest": 0,
    "ChildShards": []
}
```

Echoing and grepping into base64 -d gives:
```bash
{"model": "ride_duration_prediction_model", "version": "Test123", "prediction"}}
```

After familiarizing and setting up linting and reformatting, we want to be able to run a script with all the CI we've done so far.

We have without makefiles:
```bash
isort .
black .
pylint --recursive=y .
pytest tests/
```

To prepare the project, run:
```bash
make setup
```

Now that we're using Terraform, we navigate to the directory and use:
```bash
terraform init
terraform plan -var-file=vars/stg.tfvars
terraform apply -var-file=vars/stg.tfvars
```

Once we've confirmed that the pipeline lands, we can test it with a test input event:
```bash
export KINESIS_STREAM_INPUT="stg_ride_events-mlops-zoomcamp"
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

Then to see records via CloudWatch, use the appropriate shardId:
```bash
KINESIS_STREAM_OUTPUT='stg_ride_predictions-mlops-zoomcamp'
SHARD='shardId-000000000000'

SHARD_ITERATOR=$(aws kinesis \
    get-shard-iterator \
        --shard-id ${SHARD} \
        --shard-iterator-type TRIM_HORIZON \
        --stream-name ${KINESIS_STREAM_OUTPUT} \
        --query 'ShardIterator' \
)

RESULT=$(aws kinesis get-records --shard-iterator "${SHARD_ITERATOR}" --limit 25)
echo "${RESULT}" | jq
```
NOTE: This is what I naively though we could test the Lambda function with.
However, this doesn't actually get at the recently put records in the output stream.
This also doesn't lead to Records being posted to the CloudWatch Logs (ase we saw in 04-deployment). 
For that, we need a print statement in the Lambda function/lambda handler.
ACTUALLY, use these commands ("LATEST" shard iterator type instead of "TRIM_HORIZON"):
```bash
OUTPUT_STREAM="stg_ride_predictions-mlops-zoomcamp"
SHARD="shardId-000000000001"                       

ITERATOR=$(aws kinesis get-shard-iterator \
  --stream-name "$OUTPUT_STREAM" \                     
  --shard-id "$SHARD" \            
  --shard-iterator-type LATEST \  
  --region us-west-1 \                
  --query 'ShardIterator' \              
  --output text)      

while true; do                  
  RESULT=$(aws kinesis get-records \
    --shard-iterator "$ITERATOR" \
    --region us-west-1)             
  ITERATOR=$(echo "$RESULT" | jq -r '.NextShardIterator')

  COUNT=$(echo "$RESULT" | jq '.Records | length')       
  if [ "$COUNT" -gt 0 ]; then
    echo "$RESULT" | jq '.Records[] | {Data: (.Data | @base64d | fromjson), Timestamp: .ApproximateArrivalTimestamp}'
    break                                                           
  fi                                                  

  sleep 1                                 
done                                       
```
This waits for new records to be put into the stream (can run the put-record command in a separate terminal) and then prints them.



