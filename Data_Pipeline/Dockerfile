# Data_Pipeline/Dockerfile
# Builds the container for the data pipeline scripts
# runs inside Airflow on GCP Compute Engine

FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/

WORKDIR /app/scripts

CMD ["python", "main.py"]