# ML_Models/scripts/Dockerfile
# Builds the container for the model health check service
# deployed as a Cloud Run service

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y gcc git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "health_check:app", "--host", "0.0.0.0", "--port", "8080"]