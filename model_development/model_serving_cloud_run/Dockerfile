# model_development/model_serving_cloud_run/Dockerfile
# Builds the container for the model serving Cloud Run service

FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONPATH=/app

WORKDIR /app

COPY model_development/model_serving_cloud_run/ ./

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["gunicorn", "--workers=1", "--threads=2", "--timeout=900", "-b", "0.0.0.0:8080", "main:app"]