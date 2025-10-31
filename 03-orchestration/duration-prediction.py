#!/usr/bin/env python
# coding: utf-8

from pathlib import Path
import pickle

import pandas as pd
import xgboost as xgb

from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
from hyperopt.pyll import scope

from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import mean_squared_error

from prefect import flow, task
from prefect.task_runners import SequentialTaskRunner

import mlflow

@task
def read_dataframe(year, month):
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_{year}-{month:02d}.parquet"
    df = pd.read_parquet(url)

    df.lpep_dropoff_datetime = pd.to_datetime(df.lpep_dropoff_datetime)
    df.lpep_pickup_datetime = pd.to_datetime(df.lpep_pickup_datetime)

    df['duration'] = df.lpep_dropoff_datetime - df.lpep_pickup_datetime
    df.duration = df.duration.apply(lambda td: td.total_seconds() / 60)

    df = df[(df.duration >= 1) & (df.duration <= 60)]

    categorical = ['PULocationID', 'DOLocationID']
    df[categorical] = df[categorical].astype(str)

    df['PU_DO'] = df['PULocationID'] + '_' + df['DOLocationID']

    return df

@task
def create_X(df, dv=None):
    categorical = ['PU_DO']
    numerical = ['trip_distance']
    dicts = df[categorical + numerical].to_dict(orient='records')

    if dv == None:
        dv = DictVectorizer(sparse=True)
        X = dv.fit_transform(dicts)
    else:
        X = dv.transform(dicts)

    return X, dv

@task
def train_model_hyperopt(X_train, y_train, X_val, y_val, dv):

    train = xgb.DMatrix(X_train, label=y_train)
    valid = xgb.DMatrix(X_val, label=y_val)

    def _objective(params):
        with mlflow.start_run():
            mlflow.set_tag("model", "xgboost")
            mlflow.log_params(params)
            booster = xgb.train(
                params=params,
                dtrain=train,
                num_boost_round=100,
                evals=[(valid, 'validation')],
                early_stopping_rounds=50
            )
            y_pred = booster.predict(valid)
            rmse = mean_squared_error(y_val, y_pred, squared=False)
            mlflow.log_metric("rmse", rmse)

        return {'loss': rmse, 'status': STATUS_OK}

    search_space = {
        'max_depth': scope.int(hp.quniform('max_depth', 4, 100, 1)),
        'learning_rate': hp.loguniform('learning_rate', -3, 0),
        'reg_alpha': hp.loguniform('reg_alpha', -5, -1),
        'reg_lambda': hp.loguniform('reg_lambda', -6, -1),
        'min_child_weight': hp.loguniform('min_child_weight', -1, 3),
        'objective': 'reg:linear',
        'seed': 42
    }

    best_result = fmin(
        fn=_objective,
        space=search_space,
        algo=tpe.suggest,
        max_evals=5,
        trials=Trials()
    )
    return best_result

@task
def train_model(X_train, y_train, X_val, y_val, dv):
    with mlflow.start_run():
        
        train = xgb.DMatrix(X_train, label=y_train)
        valid = xgb.DMatrix(X_val, label=y_val)

        best_params = {
            'learning_rate': 0.09585355369315604,
            'max_depth': 30,
            'min_child_weight': 1.060597050922164,
            'objective': 'reg:linear',
            'reg_alpha': 0.018060244040060163,
            'reg_lambda': 0.011658731377413597,
            'seed': 42
        }

        mlflow.log_params(best_params)

        booster = xgb.train(
            params=best_params,
            dtrain=train,
            # num_boost_round=1000,
            num_boost_round=30,
            evals=[(valid, 'validation')],
            early_stopping_rounds=50
        )

        y_pred = booster.predict(valid)
        rmse = mean_squared_error(y_val, y_pred, squared=False)
        mlflow.log_metric("rmse", rmse)

        with open("models/preprocessor.b", "wb") as f_out:
            pickle.dump(dv, f_out)
        mlflow.log_artifact("models/preprocessor.b", artifact_path="preprocessor")

        mlflow.xgboost.log_model(booster, artifact_path="models_mlflow")

@flow(task_runner=SequentialTaskRunner())
def run(year, month):
    df_train = read_dataframe(year=year, month=month).result()

    next_year = year if month < 12 else year + 1
    next_month = month + 1 if month < 12 else 1
    df_val = read_dataframe(year=next_year, month=next_month).result()

    X_train, dv = create_X(df_train).result()
    X_val, _ = create_X(df_val, dv).result()

    target = 'duration'
    y_train = df_train[target].values
    y_val = df_val[target].values

    train_model_hyperopt(X_train, y_train, X_val, y_val, dv).result()
    train_model(X_train, y_train, X_val, y_val, dv).result()

if __name__ == "__main__":
    # Use argparse to take user input
    import argparse

    parser = argparse.ArgumentParser("Train a model to predict taxi trip duration.")
    parser.add_argument('--year', type=int, required=True, help="Input the year of taxi data to train the model on.")
    parser.add_argument('--month', type=int, required=True, help="Input the month of taxi data to train the model on.")
    args = parser.parse_args()

    models_folder = Path("models")
    models_folder.mkdir(exist_ok=True)

    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment("nyc-taxi-experiment")

    run(year=args.year, month=args.month)
    
