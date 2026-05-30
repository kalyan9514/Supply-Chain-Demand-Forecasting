"""
Data_Pipeline/scripts/utils.py

Shared utility functions for the data pipeline.
Covers GCP credentials setup, GCS bucket operations,
email alerting, and validation error collection.
"""

import io
import json
import os
import smtplib
from email.message import EmailMessage

import pandas as pd
import polars as pl
from dotenv import load_dotenv
from google.cloud import storage

try:
    from logger import logger
except ImportError:
    from Data_Pipeline.scripts.logger import logger

load_dotenv()


def setup_gcp_credentials() -> None:
    """
    Write the GCP service account key from environment variable to a local file
    and set GOOGLE_APPLICATION_CREDENTIALS to point to it.
    """
    gcp_key = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    if not gcp_key:
        logger.warning("GCP_SERVICE_ACCOUNT_KEY not set in environment.")
        return

    key_path = "/tmp/gcp-key.json"
    with open(key_path, "w") as f:
        f.write(gcp_key)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    logger.info("GCP credentials written to %s", key_path)


def load_bucket_data(bucket_name: str, blob_name: str) -> pl.DataFrame:
    """
    Load a CSV or Excel file from a GCS bucket into a Polars DataFrame.
    """
    setup_gcp_credentials()
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    content = blob.download_as_bytes()
    logger.info("Downloaded %s from bucket %s.", blob_name, bucket_name)

    if blob_name.endswith(".csv"):
        return pl.read_csv(io.BytesIO(content))
    elif blob_name.endswith((".xlsx", ".xls")):
        return pl.read_excel(io.BytesIO(content))
    else:
        raise ValueError(f"Unsupported file format: {blob_name}")


def upload_to_gcs(
    bucket_name: str,
    blob_name: str,
    data: pl.DataFrame,
) -> None:
    """
    Upload a Polars DataFrame as a CSV file to a GCS bucket.
    """
    setup_gcp_credentials()
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    csv_bytes = data.write_csv().encode("utf-8")
    blob.upload_from_string(csv_bytes, content_type="text/csv")
    logger.info("Uploaded %s to bucket %s.", blob_name, bucket_name)


def delete_blob_from_bucket(bucket_name: str, blob_name: str) -> None:
    """Delete a specific blob from a GCS bucket."""
    setup_gcp_credentials()
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.delete()
    logger.info("Deleted %s from bucket %s.", blob_name, bucket_name)


def list_bucket_blobs(bucket_name: str, prefix: str = "") -> list[str]:
    """List all blob names in a GCS bucket with an optional prefix filter."""
    setup_gcp_credentials()
    client = storage.Client()
    blobs = client.list_blobs(bucket_name, prefix=prefix)
    names = [blob.name for blob in blobs]
    logger.info("Found %d blobs in bucket %s.", len(names), bucket_name)
    return names


def send_email(
    subject: str,
    body: str,
    to_email: str,
    attachment_path: str | None = None,
) -> None:
    """
    Send an email alert via SMTP.
    Credentials are loaded from SMTP_EMAIL and SMTP_PASSWORD env vars.
    """
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_email or not smtp_password:
        logger.warning("SMTP credentials not set. Skipping email alert.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg.set_content(body)

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="octet-stream",
                filename=os.path.basename(attachment_path),
            )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(smtp_email, smtp_password)
            smtp.send_message(msg)
        logger.info("Email sent to %s: %s", to_email, subject)
    except Exception as e:
        logger.error("Failed to send email: %s", e)


def send_anomaly_alert(message: str) -> None:
    """Send a pre-formatted anomaly alert email to the configured address."""
    to_email = os.getenv("SMTP_EMAIL", "")
    send_email(
        subject="Supply Chain Pipeline: Anomaly Detected",
        body=message,
        to_email=to_email,
    )


def collect_validation_errors(
    df: pl.DataFrame,
    error_mask: pl.Series,
    error_message: str,
) -> list[dict]:
    """
    Collect rows that failed a validation check into a list of error dicts.
    Each dict contains the row index, the error message, and the row data.
    """
    error_rows = df.filter(error_mask)
    errors = []
    for i, row in enumerate(error_rows.iter_rows(named=True)):
        errors.append({
            "index": i,
            "error": error_message,
            "data": row,
        })
    return errors
