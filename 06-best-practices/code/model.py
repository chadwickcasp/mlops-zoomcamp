import os
import json
import boto3
import base64

import mlflow

AWS_REGION = os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION') or 'us-west-1'
os.environ.setdefault('AWS_REGION', AWS_REGION)
# kinesis_client = boto3.client('kinesis', region_name=AWS_REGION) 

def get_model_location(run_id: str):
    model_location = os.getenv('MODEL_LOCATION')

    if model_location is not None:
        return model_location

    model_bucket = os.getenv('MODEL_BUCKET', 'mlflow-artifacts-remote433')
    experiment_id = os.getenv('EXPERIMENT_ID', '1')

    model_location = f's3://{model_bucket}/{experiment_id}/{run_id}/artifacts/model'
    return model_location

def load_model(run_id: str):
    model_path = get_model_location(run_id)
    return mlflow.pyfunc.load_model(model_path)

def base64_decode(encoded_data: str):
    decoded_data = base64.b64decode(encoded_data).decode('utf-8')
    return json.loads(decoded_data)

class ModelService:
    def __init__(self, model: mlflow.pyfunc.PyFuncModel, model_version: str = None, callbacks=None):
        self.model = model
        self.model_version = model_version
        self.callbacks = callbacks or []

    def prepare_features(self, ride):
        features = {}
        features["PU_DO"] = f"{ride['PULocationID']}_{ride['DOLocationID']}"
        features["trip_distance"] = ride["trip_distance"]
        return features

    def predict(self, features):
        preds = self.model.predict(features)
        return float(preds[0])
        # return 10.0
        
    def lambda_handler(self, event, context):
        # pylint: disable=unused-argument

        # print(json.dumps(event))
        prediction_events = []

        for record in event['Records']:
            encoded_data = record['kinesis']['data']
            ride_event = base64_decode(encoded_data)
            # print(ride_event)
            ride = ride_event['ride']
            ride_id = ride_event['ride_id']

            features = self.prepare_features(ride)
            prediction = self.predict(features)

            prediction_event = {
                'model': 'ride_duration_prediction_model',
                'version': self.model_version,
                'prediction': {
                    'ride_duration': prediction,
                    'ride_id': ride_id,
                },
            }

            for callback in self.callbacks:
                callback(prediction_event)

            prediction_events.append(prediction_event)

        return {'prediction_events': prediction_events}

class KinesisCallback():
    def __init__(self, kinesis_client, prediction_stream_name):
        self.kinesis_client = kinesis_client
        self.prediction_stream_name = prediction_stream_name

    def put_record(self, prediction_event):
        ride_id = prediction_event['prediction']['ride_id']
        self.kinesis_client.put_record(
            StreamName = self.prediction_stream_name,
            Data = json.dumps(prediction_event),
            PartitionKey = str(ride_id),
        )

def create_kinesis_client():
    endpoint_url = os.getenv('KINESIS_ENDPOINT_URL')
    if endpoint_url is not None:
        return boto3.client('kinesis', region_name=AWS_REGION, endpoint_url=endpoint_url)
    return boto3.client('kinesis', region_name=AWS_REGION)

def init(predictions_stream_name: str, run_id: str, test_run: bool):
    model = load_model(run_id)

    callbacks = []
    if not test_run:
        kinesis_client = create_kinesis_client()
        callbacks.append(KinesisCallback(kinesis_client, predictions_stream_name).put_record)
        
    model_service = ModelService(model, model_version=run_id, callbacks=callbacks)
    return model_service
