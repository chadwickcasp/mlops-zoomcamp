# Integration test for the batch.py script

# Use data from test_prepare_data and save to s3
import os
import pandas as pd
from datetime import datetime
from tests.test_batch import dt
from batch import get_input_path, get_output_path


options = {
    'client_kwargs': {
        'endpoint_url': os.getenv('S3_ENDPOINT_URL')
    }
}
data = [
    (None, None, dt(1, 2), dt(1, 10)),
    (1, 1, dt(1, 2), dt(1, 10)),
    (1, 1, dt(1, 2, 0), dt(1, 2, 50)),
    (1, 1, dt(1, 2, 0), dt(2, 2, 1)),
]
columns = ['PUlocationID', 'DOlocationID', 'pickup_datetime', 'dropOff_datetime']
df_input = pd.DataFrame(data, columns=columns)
input_file = get_input_path(2021, 1)
df_input.to_parquet(
    input_file,
    engine='pyarrow',
    compression=None,
    index=False,
    storage_options=options
)

output_file = get_output_path(2021, 1)
os.system(f"python batch.py 2021 1")
df_output = pd.read_parquet(output_file, storage_options=options)
print(f'df_output: {df_output}')
print(f'df_output sum of durations: {df_output["predicted_duration"].sum()}')

expected = [
    ("2021/01_0", 23.1),
    ("2021/01_1", 46.2),
]
# expected_columns = ['PUlocationID', 'DOlocationID', 'pickup_datetime', 'dropOff_datetime', 'duration']
expected_columns = ['ride_id', 'predicted_duration']
expected_df = pd.DataFrame(expected, columns=expected_columns)
print(f'expected_df: {expected_df}')
pd.testing.assert_frame_equal(df_output, expected_df)
