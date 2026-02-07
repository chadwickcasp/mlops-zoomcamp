import batch
import pandas as pd
from datetime import datetime

def dt(hour, minute, second=0):
    return datetime(2021, 1, 1, hour, minute, second)

categorical = ['PUlocationID', 'DOlocationID']

def test_prepare_data():
    data = [
        (None, None, dt(1, 2), dt(1, 10)),
        (1, 1, dt(1, 2), dt(1, 10)),
        (1, 1, dt(1, 2, 0), dt(1, 2, 50)),
        (1, 1, dt(1, 2, 0), dt(2, 2, 1)),
    ]

    columns = ['PUlocationID', 'DOlocationID', 'pickup_datetime', 'dropOff_datetime']
    df = pd.DataFrame(data, columns=columns)
    df = batch.prepare_data(df, categorical=categorical)
    expected = [
        ("-1", "-1", dt(1, 2), dt(1, 10), 8.0),
        ("1", "1", dt(1, 2), dt(1, 10), 8.0),
    ]
    expected_columns = ['PUlocationID', 'DOlocationID', 'pickup_datetime', 'dropOff_datetime', 'duration']
    expected_df = pd.DataFrame(expected, columns=expected_columns)
    pd.testing.assert_frame_equal(df, expected_df)
