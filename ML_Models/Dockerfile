# ML_Models/Dockerfile
# Builds the container for model training jobs
# triggered via Cloud Run and executed on Vertex AI

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y gcc git && rm -rf /var/lib/apt/lists/*

COPY ML_Models/requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --no-warn-script-location -r /app/requirements.txt

COPY Data_Pipeline/scripts/ /app/Data_Pipeline/scripts/
COPY ML_Models/scripts/ /app/ML_Models/scripts/
COPY model_development/model_training/ /app/model_development/model_training/

WORKDIR /app/ML_Models/scripts

CMD ["python", "model_lstm.py"]