import lambda_function

event = {
    "Records": [
        {
            "kinesis": {
                "kinesisSchemaVersion": "1.0",
                "partitionKey": "1",
                "sequenceNumber": "49668913391720301661695968124856985088142789787609202690",
                "data": "ewogICAgICAgICJyaWRlIjogewogICAgICAgICAgICAiUFVMb2NhdGlvbklEIjogMTMwLAogICAgICAgICAgICAiRE9Mb2NhdGlvbklEIjogMjA1LAogICAgICAgICAgICAidHJpcF9kaXN0YW5jZSI6IDMuNjYKICAgICAgICB9LCAKICAgICAgICAicmlkZV9pZCI6IDE1NgogICAgfQ==",
                "approximateArrivalTimestamp": 1762991576.545
            },
            "eventSource": "aws:kinesis",
            "eventVersion": "1.0",
            "eventID": "shardId-000000000000:49668913391720301661695968124856985088142789787609202690",
            "eventName": "aws:kinesis:record",
            "invokeIdentityArn": "arn:aws:iam::413093438819:role/lambda-kinesis-role",
            "awsRegion": "us-west-1",
            "eventSourceARN": "arn:aws:kinesis:us-west-1:413093438819:stream/ride-events-1"
        }
    ]
}

result = lambda_function.lambda_handler(event, None)
print(result)
