"""
backend/main.py

FastAPI backend for the Supply Chain Demand Forecasting system.
Provides endpoints for file uploads, demand forecasting,
data retrieval, validation, and scheduler management.
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from google.cloud import aiplatform, scheduler_v1, storage
from sqlalchemy import text

from model_training_utils import get_db_engine

try:
    from logger import logger
except ImportError:
    from Data_Pipeline.scripts.logger import logger

load_dotenv()

app = FastAPI(title="Supply Chain Demand Forecasting API")

API_TOKEN = os.getenv("API_TOKEN", "")
GCS_UPLOAD_BUCKET = os.getenv("GCS_UPLOAD_BUCKET", "")
AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "")
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
REGION = os.getenv("GCP_LOCATION", "us-central1")
VERTEX_ENDPOINT_ID = os.getenv("VERTEX_ENDPOINT_ID", "")


def verify_token(token: str = Header(...)):
    """Validate the API token from the request header."""
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def get_storage_client():
    """Return an authenticated GCS storage client."""
    return storage.Client()


@app.get("/health")
def health():
    """Basic health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    token: str = Depends(verify_token),
):
    """
    Upload an Excel file to GCS and trigger the Airflow preprocessing DAG.
    Returns the GCS blob path and DAG run ID.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files are supported.")

    contents = await file.read()
    blob_name = f"raw/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"

    client = get_storage_client()
    bucket = client.bucket(GCS_UPLOAD_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(contents, content_type=file.content_type)
    logger.info("Uploaded %s to GCS bucket %s.", blob_name, GCS_UPLOAD_BUCKET)

    dag_run_id = None
    if AIRFLOW_API_URL:
        try:
            response = requests.post(
                f"{AIRFLOW_API_URL}/api/v1/dags/gcp_preprocessing_on_demand/dagRuns",
                json={
                    "conf": {"blob_name": blob_name, "bucket": GCS_UPLOAD_BUCKET},
                    "dag_run_id": f"upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                },
                auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
                timeout=10,
            )
            dag_run_id = response.json().get("dag_run_id")
            logger.info("Airflow DAG triggered: %s", dag_run_id)
        except Exception as e:
            logger.warning("Could not trigger Airflow DAG: %s", e)

    return JSONResponse(
        status_code=200,
        content={"blob_name": blob_name, "dag_run_id": dag_run_id},
    )


@app.get("/data")
def get_data(
    n: int = Query(default=50, ge=1, le=1000),
    predictions: str = Query(default="False"),
    token: str = Depends(verify_token),
):
    """
    Retrieve the most recent n records from Cloud SQL.
    Set predictions=True to include model predictions alongside actuals.
    """
    engine = get_db_engine()
    table = "predictions" if predictions.lower() == "true" else "transactions"

    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT * FROM {table} ORDER BY date DESC LIMIT :n"),
            {"n": n},
        )
        rows = [dict(row._mapping) for row in result]

    logger.info("Fetched %d rows from %s.", len(rows), table)
    return JSONResponse(status_code=200, content={"data": rows, "count": len(rows)})


@app.get("/stats")
def get_stats(token: str = Depends(verify_token)):
    """
    Return summary statistics for the last 30 days of sales data.
    """
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT "
                "MIN(date) as start_date, "
                "MAX(date) as end_date, "
                "COUNT(*) as total_entries, "
                "COUNT(DISTINCT product_name) as total_products, "
                "SUM(total_quantity) as total_quantity "
                "FROM transactions "
                "WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
            )
        )
        row = dict(result.fetchone()._mapping)

    return JSONResponse(status_code=200, content=row)


@app.post("/predict")
def predict(
    days: int = Query(default=7, ge=1, le=90),
    token: str = Depends(verify_token),
):
    """
    Trigger the Vertex AI model endpoint to generate demand forecasts
    for the next n days. Stores predictions in Cloud SQL.
    """
    if not VERTEX_ENDPOINT_ID:
        raise HTTPException(status_code=503, detail="Vertex AI endpoint not configured.")

    try:
        aiplatform.init(project=PROJECT_ID, location=REGION)
        endpoint = aiplatform.Endpoint(endpoint_name=VERTEX_ENDPOINT_ID)

        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT date, product_name, total_quantity "
                    "FROM transactions "
                    "ORDER BY date DESC LIMIT 30"
                )
            )
            recent_data = [dict(row._mapping) for row in result]

        prediction = endpoint.predict(instances=recent_data)
        logger.info("Vertex AI prediction complete for %d days.", days)

        return JSONResponse(
            status_code=200,
            content={"days": days, "predictions": prediction.predictions},
        )
    except Exception as e:
        logger.error("Prediction failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate")
async def validate_file(
    file: UploadFile = File(...),
    token: str = Depends(verify_token),
):
    """
    Validate the structure and content of an uploaded Excel file
    before it enters the pipeline.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files are supported.")

    contents = await file.read()
    import io
    df = pd.read_excel(io.BytesIO(contents))

    required_columns = ["Date", "Product Name", "Total Quantity"]
    missing = [c for c in required_columns if c not in df.columns]

    if missing:
        return JSONResponse(
            status_code=422,
            content={"valid": False, "missing_columns": missing},
        )

    unknown_products = []
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT product_name FROM transactions"))
        known_products = {row[0] for row in result}

    if "Product Name" in df.columns:
        unknown_products = [
            p for p in df["Product Name"].unique()
            if p not in known_products
        ]

    return JSONResponse(
        status_code=200,
        content={
            "valid": True,
            "rows": len(df),
            "columns": df.columns.tolist(),
            "unknown_products": unknown_products,
        },
    )


@app.put("/scheduler")
def update_scheduler(
    cron: str = Query(..., description="Cron expression for the scheduler"),
    token: str = Depends(verify_token),
):
    """
    Update the GCP Cloud Scheduler job with a new cron expression.
    """
    job_name = f"projects/{PROJECT_ID}/locations/{REGION}/jobs/prediction-job"
    client = scheduler_v1.CloudSchedulerClient()

    try:
        job = client.get_job(name=job_name)
        job.schedule = cron
        updated = client.update_job(job=job, update_mask={"paths": ["schedule"]})
        logger.info("Scheduler updated to: %s", cron)
        return JSONResponse(
            status_code=200,
            content={"job": updated.name, "schedule": updated.schedule},
        )
    except Exception as e:
        logger.error("Failed to update scheduler: %s", e)
        raise HTTPException(status_code=500, detail=str(e))