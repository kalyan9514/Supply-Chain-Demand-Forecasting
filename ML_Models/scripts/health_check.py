"""
ML_Models/scripts/health_check.py

FastAPI service that validates model predictions via statistical checks.
Exposes a /model/health endpoint that returns 30-day model diagnostics
including RMSE, KS-test drift detection, and overall health status.
"""

import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import monitoring_v3

from model_training_utils import (
    get_latest_data_from_cloud_sql,
    ks_test_drift,
)

try:
    from logger import logger
except ImportError:
    from Data_Pipeline.scripts.logger import logger

load_dotenv()

app = FastAPI(title="Model Health Check")

API_TOKEN = os.getenv("API_TOKEN", "")
RMSE_THRESHOLD = 18.0
LOOKBACK_DAYS = 30


def verify_token(token: str = Header(...)):
    """Validate the API token from the request header."""
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def compute_rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Compute root mean squared error between actual and predicted values."""
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def send_metric_to_cloud_monitoring(
    project_id: str,
    metric_type: str,
    value: float,
) -> None:
    """Write a custom metric to Google Cloud Monitoring."""
    try:
        client = monitoring_v3.MetricServiceClient()
        project_name = f"projects/{project_id}"

        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/{metric_type}"
        series.resource.type = "global"

        point = monitoring_v3.Point()
        point.value.double_value = value
        now = monitoring_v3.TimeInterval()
        import time
        now.end_time.seconds = int(time.time())
        point.interval = now
        series.points = [point]

        client.create_time_series(name=project_name, time_series=[series])
        logger.info("Metric %s = %.4f sent to Cloud Monitoring.", metric_type, value)
    except Exception as e:
        logger.warning("Failed to send metric to Cloud Monitoring: %s", e)


@app.post("/model/health")
def model_health(token: str = Depends(verify_token)):
    """
    Run a 30-day model health check.

    Returns RMSE, KS-test drift results per product,
    and an overall healthy/unhealthy status.
    """
    try:
        df = get_latest_data_from_cloud_sql(days=LOOKBACK_DAYS, table="predictions")

        if df.empty:
            return JSONResponse(
                status_code=200,
                content={"status": "no_data", "message": "No predictions found in the last 30 days."},
            )

        results = {}
        overall_healthy = True

        for product in df["product_name"].unique():
            product_df = df[df["product_name"] == product]

            if "actual_quantity" not in product_df.columns or "predicted_quantity" not in product_df.columns:
                continue

            actual = product_df["actual_quantity"].values
            predicted = product_df["predicted_quantity"].values

            rmse = compute_rmse(actual, predicted)
            drift = ks_test_drift(actual, predicted)

            product_healthy = rmse <= RMSE_THRESHOLD and not drift["drift_detected"]
            if not product_healthy:
                overall_healthy = False

            results[product] = {
                "rmse": round(rmse, 4),
                "ks_statistic": round(drift["ks_statistic"], 4),
                "p_value": round(drift["p_value"], 4),
                "drift_detected": drift["drift_detected"],
                "healthy": product_healthy,
            }

        project_id = os.getenv("GCP_PROJECT_ID", "")
        if project_id:
            avg_rmse = float(np.mean([r["rmse"] for r in results.values()]))
            send_metric_to_cloud_monitoring(project_id, "supply_chain/model_rmse", avg_rmse)

        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy" if overall_healthy else "unhealthy",
                "rmse_threshold": RMSE_THRESHOLD,
                "products": results,
            },
        )

    except Exception as e:
        logger.error("Health check failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
    