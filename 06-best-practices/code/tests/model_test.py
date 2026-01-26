import pathlib

import model


def read_text_file(filename):
    script_dir = pathlib.Path(__file__).parent
    filename = script_dir / filename
    with open(filename, 'rt', encoding='utf-8') as file:
        return file.read().strip()


def test_base64_decode():
    encoded_data = read_text_file('data.b64')
    actual_ride_event = model.base64_decode(encoded_data)
    expected_ride_event = {
        "ride": {
            "PULocationID": 130,
            "DOLocationID": 205,
            "trip_distance": 3.66,
        },
        "ride_id": 156,
    }
    assert actual_ride_event == expected_ride_event


def test_prepare_features():
    model_service = model.ModelService(None)

    ride = {
        "PULocationID": 130,
        "DOLocationID": 205,
        "trip_distance": 3.66,
    }

    actual_features = model_service.prepare_features(ride)

    expected_features = {
        "PU_DO": "130_205",
        # "PU_DO": "130_206",
        "trip_distance": 3.66,
    }
    assert actual_features == expected_features


class ModelMock:
    def __init__(self, value):
        self.value = value

    def predict(self, X):
        n = len(X)
        return [self.value] * n


def test_predict():
    model_mock = ModelMock(18.168945726405333)
    model_service = model.ModelService(model_mock, "123")
    features = {
        "PU_DO": "130_205",
        "trip_distance": 3.66,
    }
    actual_prediction = model_service.predict(features)
    expected_prediction = 18.168945726405333
    assert actual_prediction == expected_prediction


def test_lambda_handler():
    model_mock = ModelMock(18.168945726405333)
    model_service = model.ModelService(model_mock, "123")

    event = {
        "Records": [
            {
                "kinesis": {
                    "data": read_text_file('data.b64'),
                },
            }
        ]
    }
    actual_prediction_events = model_service.lambda_handler(event, None)
    expected_prediction_events = {
        'prediction_events': [
            {
                'model': 'ride_duration_prediction_model',
                'version': "123",
                'prediction': {
                    'ride_duration': 18.168945726405333,
                    'ride_id': 156,
                },
            }
        ]
    }
    assert actual_prediction_events == expected_prediction_events
