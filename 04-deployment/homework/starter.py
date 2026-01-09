#!/usr/bin/env python
# coding: utf-8
import argparse
import boto3
import pickle
import pandas as pd

categorical = ['PUlocationID', 'DOlocationID']
s3 = boto3.client('s3')

def read_data(filename):
    df = pd.read_parquet(filename)
    
    df['duration'] = df.dropOff_datetime - df.pickup_datetime
    df['duration'] = df.duration.dt.total_seconds() / 60

    df = df[(df.duration >= 1) & (df.duration <= 60)].copy()

    df[categorical] = df[categorical].fillna(-1).astype('int').astype('str')
    
    return df

def apply_model(year, month):
    with open('model.bin', 'rb') as f_in:
        dv, lr = pickle.load(f_in)

    df = read_data(f'https://d37ci6vzurychx.cloudfront.net/trip-data/fhv_tripdata_{year:04d}-{month:02d}.parquet')

    dicts = df[categorical].to_dict(orient='records')
    X_val = dv.transform(dicts)
    y_pred = lr.predict(X_val)

    print(y_pred.mean())

    df['ride_id'] = f'{year:04d}/{month:02d}_'+df.index.astype('str')
    df_result = pd.DataFrame()
    df_result['ride_id'] = df['ride_id']
    df_result['predicted_duration'] = y_pred
    output_file = f'results_{year:04d}_{month:02d}.parquet'
    df_result.to_parquet(
        output_file,
        engine='pyarrow',
        compression=None,
        index=False
    )
 
    key = f'predictions/{year:04d}/{month:02d}/{output_file}'
    s3.upload_file(
        output_file,
        'mlflow-artifacts-remote433',
        key
    )

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--year',
        default=2021,
        type=int,
        help='Year of the data to be processed'
    )
    parser.add_argument(
        '--month',
        default=2,
        type=int,
        help='Month of the data to be processed'
    )
    args = parser.parse_args()
    apply_model(args.year, args.month)

