#!/usr/bin/env bash
# Minimal script to send a test ride event to the source Kinesis stream
# and check if predictions appear in the output stream
SOURCE_STREAM="${SOURCE_STREAM:-stg_ride_events-mlops-zoomcamp}"
OUTPUT_STREAM="${OUTPUT_STREAM:-stg_ride_predictions-mlops-zoomcamp}"
: "${AWS_DEFAULT_REGION:=us-west-1}"

echo "Sending test event to $SOURCE_STREAM..."

PUT_RESULT=$(aws kinesis put-record \
  --stream-name "$SOURCE_STREAM" \
  --partition-key 1 \
  --cli-binary-format raw-in-base64-out \
  --data '{
    "ride": {
        "PULocationID": 130,
        "DOLocationID": 205,
        "trip_distance": 3.66
    }, 
    "ride_id": 156
}' \
  --region "$AWS_DEFAULT_REGION" \
  --output json 2>&1)

if [[ $? -eq 0 && -n "$PUT_RESULT" ]]; then
  echo "$PUT_RESULT" | jq '{ShardId:.ShardId,SequenceNumber:.SequenceNumber}'
  echo "✓ Event sent successfully"
else
  echo "✗ Failed to send event: $PUT_RESULT"
  exit 1
fi

echo ""
echo "Waiting 15s for Lambda to process..."
sleep 15

echo ""
echo "Checking output stream: $OUTPUT_STREAM"

# Get shards and check for records
SHARDS=$(aws kinesis describe-stream \
  --stream-name "$OUTPUT_STREAM" \
  --region "$AWS_DEFAULT_REGION" \
  --query 'StreamDescription.Shards[].ShardId' \
  --output text)

TOTAL_RECORDS=0
for SHARD in $SHARDS; do
  [[ -z "$SHARD" ]] && continue
  
  SHARD_ITERATOR=$(aws kinesis get-shard-iterator \
    --stream-name "$OUTPUT_STREAM" \
    --shard-id "$SHARD" \
    --shard-iterator-type TRIM_HORIZON \
    --region "$AWS_DEFAULT_REGION" \
    --query 'ShardIterator' \
    --output text 2>/dev/null)
  
  if [[ -n "$SHARD_ITERATOR" ]]; then
    RESULT=$(aws kinesis get-records \
      --shard-iterator "$SHARD_ITERATOR" \
      --limit 10 \
      --region "$AWS_DEFAULT_REGION" 2>/dev/null)
    
    COUNT=$(echo "$RESULT" | jq -r '.Records | length' 2>/dev/null || echo "0")
    if [[ "$COUNT" =~ ^[0-9]+$ ]] && [[ "$COUNT" -gt 0 ]]; then
      TOTAL_RECORDS=$((TOTAL_RECORDS + COUNT))
      echo "  Shard $SHARD: Found $COUNT record(s)"
      echo "$RESULT" | jq '.Records[0] | {Data: (.Data | @base64d | fromjson), ApproximateArrivalTimestamp: .ApproximateArrivalTimestamp}'
    else
      echo "  Shard $SHARD: No records found"
    fi
  fi
done

echo ""
if [[ $TOTAL_RECORDS -gt 0 ]]; then
  echo "✓ SUCCESS: Found $TOTAL_RECORDS record(s) in output stream"
else
  echo "✗ No records found in output stream"
  echo "  Check Lambda CloudWatch logs for errors"
fi
