from prefect import flow

@flow
def myflow():
    print("Hello, Prefect!")

from prefect.deployments import DeploymentSpec
from prefect.orion.schemas.schedules import IntervalSchedule
from prefect.flow_runners import SubprocessFlowRunner
from datetime import timedelta

deployment_dev = DeploymentSpec(flow=myflow,
                                name="model_training-dev",
                                schedule=IntervalSchedule(interval=timedelta(minutes=5)),
                                flow_runner=SubprocessFlowRunner(),
                                tags=["dev"])

deployment_prod = DeploymentSpec(flow=myflow,
                                name="model_training-prod",
                                schedule=IntervalSchedule(interval=timedelta(minutes=5)),
                                flow_runner=SubprocessFlowRunner(),
                                tags=["prod"])

