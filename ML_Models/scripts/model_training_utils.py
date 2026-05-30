"""
ML_Models/scripts/model_training_utils.py

Shared utilities for model training scripts.
Covers Cloud SQL access, feature engineering, bias detection,
email alerts, and GCS artifact uploads.
"""

import os
import logging
import pickle
from datetime import timedelta

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from google.cloud import storage
from scipy import stats
from sklearn.preprocessing import LabelEncoder
from sqlalchemy import create_engine, text

try:
    from logger import logger
except ImportError:
    from Data_Pipeline.scripts.logger import logger

load_dotenv()


def get_db_engine():
    """Create and return a SQLAlchemy engine for Cloud SQL."""
    host = os.getenv("MYSQL_HOST")
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    database = os.getenv("MYSQL_DATABASE")

    connection_string = (
        f"mysql+pymysql://{user}:{password}@{host}/{database}"
    )
    return create_engine(connection_string)


def get_latest_data_from_cloud_sql(
    days: int = 365,
    table: str = "transactions",
) -> pd.DataFrame:
    """
    Fetch the most recent records from Cloud SQL.
    Returns a DataFrame with the last n days of data.
    """
    engine = get_db_engine()
    query = text(
        f"SELECT * FROM {table} "
        f"WHERE date >= DATE_SUB(CURDATE(), INTERVAL :days DAY) "
        f"ORDER BY date ASC"
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"days": days})
    logger.info("Fetched %d rows from Cloud SQL table %s.", len(df), table)
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add time-based lag and rolling statistical features
    for demand forecasting.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["product_name", "date"])

    for lag in [1, 7, 14, 30]:
        df[f"lag_{lag}"] = df.groupby("product_name")["total_quantity"].shift(lag)

    for window in [7, 14, 30]:
        df[f"rolling_mean_{window}"] = (
            df.groupby("product_name")["total_quantity"]
            .transform(lambda x: x.rolling(window, min_periods=1).mean())
        )
        df[f"rolling_std_{window}"] = (
            df.groupby("product_name")["total_quantity"]
            .transform(lambda x: x.rolling(window, min_periods=1).std().fillna(0))
        )

    df["month"] = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    encoder = LabelEncoder()
    df["product_encoded"] = encoder.fit_transform(df["product_name"])

    df = df.dropna()
    return df


def detect_bias(
    df: pd.DataFrame,
    prediction_col: str = "predicted_quantity",
    actual_col: str = "total_quantity",
    group_col: str = "product_name",
) -> dict:
    """
    Detect per-group prediction bias using RMSE and MAPE disparity ratios.
    Returns a dict with per-group metrics and disparity ratios.
    """
    results = {}
    groups = df[group_col].unique()

    for group in groups:
        group_df = df[df[group_col] == group]
        actual = group_df[actual_col].values
        predicted = group_df[prediction_col].values

        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        mape = np.mean(np.abs((actual - predicted) / (actual + 1e-8))) * 100
        results[group] = {"rmse": rmse, "mape": mape}

    rmse_values = [v["rmse"] for v in results.values()]
    mape_values = [v["mape"] for v in results.values()]

    disparity = {
        "per_group": results,
        "rmse_disparity_ratio": max(rmse_values) / (min(rmse_values) + 1e-8),
        "mape_disparity_ratio": max(mape_values) / (min(mape_values) + 1e-8),
    }
    logger.info("Bias detection complete. RMSE disparity: %.2f", disparity["rmse_disparity_ratio"])
    return disparity


def upload_artifact_to_gcs(
    local_path: str,
    bucket_name: str,
    destination_blob: str,
) -> None:
    """Upload a local file to a GCS bucket."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)
    blob.upload_from_filename(local_path)
    logger.info("Uploaded %s to gs://%s/%s.", local_path, bucket_name, destination_blob)


def upload_pickle_to_gcs(
    local_pickle_path: str,
    bucket_name: str,
    destination_blob_name: str,
) -> None:
    """Upload a pickle file to a GCS bucket."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(
        local_pickle_path, content_type="application/octet-stream"
    )
    logger.info(
        "Pickle uploaded to gs://%s/%s.", bucket_name, destination_blob_name
    )


def ks_test_drift(
    reference: np.ndarray,
    current: np.ndarray,
) -> dict:
    """
    Run a Kolmogorov-Smirnov test to detect data drift
    between a reference distribution and the current distribution.
    """
    stat, p_value = stats.ks_2samp(reference, current)
    drift_detected = p_value < 0.05
    logger.info(
        "KS test: statistic=%.4f, p-value=%.4f, drift=%s",
        stat, p_value, drift_detected,
    )
    return {
        "ks_statistic": stat,
        "p_value": p_value,
        "drift_detected": drift_detected,
    }
