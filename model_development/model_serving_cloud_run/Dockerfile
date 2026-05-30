# model_development/model_training_cloud_run_trigger/Dockerfile
# Builds the container for the training trigger Cloud Run service

FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONPATH=/app

WORKDIR /app

COPY model_development/model_training_cloud_run_trigger/ ./

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "1800", "main:app"]
