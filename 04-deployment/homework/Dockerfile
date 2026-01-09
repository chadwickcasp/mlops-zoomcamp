FROM agrigorev/zoomcamp-model:mlops-3.9.7-slim

# Copy function code
COPY starter.py ./

# Install pipenv and then the specified packages
COPY Pipfile Pipfile.lock ./
RUN pip install -U pip
RUN pip install pipenv && pipenv install --system --deploy

# Run the script with default arguments
ENTRYPOINT [ "python", "starter.py"] 
CMD [ "--year", "2021", "--month", "2" ]
