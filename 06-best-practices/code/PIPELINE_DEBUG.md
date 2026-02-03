# Pipeline debug: no Records in predictions stream

If Lambda runs without errors but you see no records in `stg_ride_predictions-mlops-zoomcamp`, check these in order.

## 1. Kinesis stream metrics (fastest)

**AWS Console → Kinesis → Data streams → `stg_ride_predictions-mlops-zoomcamp` → Monitoring**

- **IncomingRecords** (or **PutRecords**): if this is 0, nothing is being written to the stream.
  - Then either Lambda is not calling `put_record` (e.g. `TEST_RUN=True` so callbacks are empty), or `put_record` is failing and you should see a Lambda error.
- If IncomingRecords &gt; 0, records are being written; the issue is how/when you read (shard, iterator type, or stream name).

## 2. Lambda environment

**AWS Console → Lambda → `stg_ride_prediction_lambda_mlops-zoomcamp` → Configuration → Environment variables**

- **TEST_RUN**: must be unset or `False`. If it is `True`, the Lambda does not write to Kinesis (callbacks are empty). Terraform now sets `TEST_RUN=False`; run `terraform apply` so it takes effect.
- **RUN_ID**: must be set (e.g. by `scripts/deploy-manual.sh`). If missing, model load fails at cold start.
- **PREDICTIONS_STREAM_NAME**: should be `stg_ride_predictions-mlops-zoomcamp` (same as the Kinesis stream name).

## 3. Lambda IAM

**AWS Console → Lambda → Configuration → Permissions → Role**

The role must allow `kinesis:PutRecord` on the predictions stream ARN. In Terraform this is the inline policy `LambdaInlinePolicy` with `Resource = var.output_stream_arn`. If that ARN is wrong or the policy was changed, PutRecord can fail with AccessDenied (Lambda would then show an error).

## 4. Reading the stream

- Use the same stream name as Lambda: `stg_ride_predictions-mlops-zoomcamp`.
- Use **TRIM_HORIZON** to read from the start, or **LATEST** and poll after sending an event.
- The stream has 2 shards; read from both (e.g. `test-stream.sh` does this).

## Summary

1. Check **Kinesis metrics** for the predictions stream (IncomingRecords).
2. Ensure **TEST_RUN** is not `True` and **RUN_ID** is set; run `terraform apply` and/or `deploy-manual.sh` as needed.
3. If metrics show writes but you still see no records, double-check stream name and shards when reading.

