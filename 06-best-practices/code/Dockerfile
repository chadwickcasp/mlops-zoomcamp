FROM public.ecr.aws/lambda/python:3.9

# Copy function code
COPY lambda_function.py model.py ./

# Install pipenv and then the specified packages
COPY Pipfile Pipfile.lock ./
RUN pip install -U pip
RUN pip install pipenv && pipenv install --system --deploy

CMD [ "lambda_function.lambda_handler" ]
