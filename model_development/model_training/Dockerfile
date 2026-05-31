# model_development/model_training/Dockerfile
# Builds the container for model training jobs
# executed on Vertex AI custom training

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y gcc git && rm -rf /var/lib/apt/lists/*

COPY Data_Pipeline/scripts/ /app/Data_Pipeline/scripts/
COPY ML_Models/scripts/ /app/ML_Models/scripts/
COPY model_development/model_training/ /app/model_development/model_training/

WORKDIR /app/model_development/model_training
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --no-warn-script-location -r requirements.txt

WORKDIR /app/ML_Models/scripts

CMD ["python", "model_lstm.py"]