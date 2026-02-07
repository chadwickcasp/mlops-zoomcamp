#!/usr/bin/env python
# coding: utf-8

import io
import sys
import pickle
import requests
import pandas as pd
import os

def get_input_path(year, month):
    default_input_pattern = 'https://d37ci6vzurychx.cloudfront.net/trip-data/fhv_tripdata_{year:04d}-{month:02d}.parquet'
    input_pattern = os.getenv('INPUT_FILE_PATTERN', default_input_pattern)
    return input_pattern.format(year=year, month=month)


def get_output_path(year, month):
    default_output_pattern = 'taxi_type=fhv_year={year:04d}_month={month:02d}.parquet'
    output_pattern = os.getenv('OUTPUT_FILE_PATTERN', default_output_pattern)
    return output_pattern.format(year=year, month=month)


def read_data(filename):
    # Read parquet didn't work with the URL, so we use requests to get the content and then read the parquet
    s3_endpoint_url = os.getenv('S3_ENDPOINT_URL')
    if filename.startswith(("http://", "https://")):
        r = requests.get(filename, timeout=300)
        r.raise_for_status()
        df = pd.read_parquet(io.BytesIO(r.content))
    elif filename.startswith('s3://') and s3_endpoint_url:
        options = {
            'client_kwargs': {
                'endpoint_url': s3_endpoint_url
            }
        }
        df = pd.read_parquet(filename, storage_options=options)
    else:
        df = pd.read_parquet(filename)
    return df

def save_data(df, filename):
    s3_endpoint_url = os.getenv('S3_ENDPOINT_URL')
    if filename.startswith('s3://') and s3_endpoint_url:
        options = {
            'client_kwargs': {
                'endpoint_url': s3_endpoint_url
            }
        }
        df.to_parquet(filename, engine='pyarrow', index=False, storage_options=options)
    else:
        df.to_parquet(filename, engine='pyarrow', index=False)

def prepare_data(df, categorical):
    df['duration'] = df.dropOff_datetime - df.pickup_datetime
    df['duration'] = df.duration.dt.total_seconds() / 60

    df = df[(df.duration >= 1) & (df.duration <= 60)].copy()

    df[categorical] = df[categorical].fillna(-1).astype('int').astype('str')
    return df

def main(year, month):
    # Input and output files didn't end up working, so we use CloudFront URL and local file name
    # input_file = f'https://raw.githubusercontent.com/alexeygrigorev/datasets/master/nyc-tlc/fhv/fhv_tripdata_{year:04d}-{month:02d}.parquet'
    # output_file = f's3://nyc-duration-prediction-alexey/taxi_type=fhv/year={year:04d}/month={month:02d}/predictions.parquet'

    # Commented for updated s3 testing
    # input_file = f'https://d37ci6vzurychx.cloudfront.net/trip-data/fhv_tripdata_{year:04d}-{month:02d}.parquet'
    # output_file = 'taxi_type=fhv_year={year:04d}_month={month:02d}.parquet'

    input_file = get_input_path(year, month)
    output_file = get_output_path(year, month)

    categorical = ['PUlocationID', 'DOlocationID']
    
    with open('model.bin', 'rb') as f_in:
        dv, lr = pickle.load(f_in)

    df = read_data(input_file)
    df = prepare_data(df, categorical)
    
    df['ride_id'] = f'{year:04d}/{month:02d}_' + df.index.astype('str')

    dicts = df[categorical].to_dict(orient='records')
    X_val = dv.transform(dicts)
    y_pred = lr.predict(X_val)

    print('predicted mean duration:', y_pred.mean())

    df_result = pd.DataFrame()
    df_result['ride_id'] = df['ride_id']
    df_result['predicted_duration'] = y_pred

    save_data(df_result, output_file)

if __name__ == '__main__':
    a, b = int(sys.argv[1]), int(sys.argv[2])
    # Accept either "year month" (2021 2) or "month year" (2 2021)
    year, month = (a, b) if a > 12 else (b, a)
    main(year, month)