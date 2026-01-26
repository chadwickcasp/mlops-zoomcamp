# pylint: disable=duplicate-code

import json

import requests
from deepdiff import DeepDiff

with open('event.json', 'rt', encoding='utf-8') as file:
    event = json.load(file)

url = 'http://localhost:8080/2015-03-31/functions/function/invocations'
actual_response = requests.post(url, json=event).json()
print(f'actual_response: {json.dumps(actual_response, indent=4)}')

expected_response = {
    'prediction_events': [
        {
            'model': 'ride_duration_prediction_model',
            # 'version': "ecfa50f261e64914817112759fbbfc48",
            'version': "Test123",
            'prediction': {
                'ride_duration': 18.17,
                'ride_id': 156,
            },
        }
    ]
}

diff = DeepDiff(actual_response, expected_response, significant_digits=2)
# diff = DeepDiff(actual_response, expected_response)
print(f'diff: {diff}')

assert 'type_changes' not in diff
assert 'values_changed' not in diff

# assert actual_response == expected_response

# print(response.json())
