# pylint: disable=duplicate-code

import os
import boto3
import json
from pprint import pprint

from deepdiff import DeepDiff

kinesis_endpoint_url = os.getenv('KINESIS_ENDPOINT_URL', 'http://localhost:4566')
kinesis_client = boto3.client('kinesis', region_name='us-west-1', endpoint_url=kinesis_endpoint_url)

stream_name = os.getenv('PREDICTIONS_STREAM_NAME', 'ride_predictions')
shard_id = 'shardId-000000000000'

shard_iterator_id = kinesis_client.get_shard_iterator(
    StreamName=stream_name,
    ShardId=shard_id,
    ShardIteratorType='TRIM_HORIZON',
)['ShardIterator']

records = kinesis_client.get_records(
    ShardIterator=shard_iterator_id,
    Limit=1,
)

records = records['Records']
pprint(f'records: {records}')

assert len(records) == 1

actual_record = json.loads(records[0]['Data'])
pprint(f'actual_record: {actual_record}')

expected_record = {
    'model': 'ride_duration_prediction_model',
    # 'version': "ecfa50f261e64914817112759fbbfc48",
    'version': "Test123",
    'prediction': {
        'ride_duration': 18.17,
        'ride_id': 156,
    }
}

diff = DeepDiff(actual_record, expected_record, significant_digits=2)
print(f'diff: {diff}')

assert 'type_changes' not in diff
assert 'values_changed' not in diff
assert 'missing_item' not in diff


print('Integration test passed')