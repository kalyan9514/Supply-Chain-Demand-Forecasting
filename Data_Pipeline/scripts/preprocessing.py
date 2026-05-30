"""
Data_Pipeline/scripts/preprocessing.py

Cleans and transforms validated raw data before model training.
Handles type conversion, feature engineering, outlier detection,
and deduplication.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import polars as pl

try:
    from logger import logger
    from post_validation import main as post_validation_main
    from utils import (
        delete_blob_from_bucket,
        list_bucket_blobs,
        load_bucket_data,
        send_anomaly_alert,
        upload_to_gcs,
    )
except ImportError:
    from Data_Pipeline.scripts.logger import logger
    from Data_Pipeline.scripts.post_validation import main as post_validation_main
    from Data_Pipeline.scripts.utils import (
        delete_blob_from_bucket,
        list_bucket_blobs,
        load_bucket_data,
        send_anomaly_alert,
        upload_to_gcs,
    )


def convert_feature_types(df: pl.DataFrame) -> pl.DataFrame:
    """Convert columns to their correct data types."""
    if "Date" in df.columns:
        df = df.with_columns(
            pl.col("Date").cast(pl.Date, strict=False)
        )
    if "Total Quantity" in df.columns:
        df = df.with_columns(
            pl.col("Total Quantity").cast(pl.Float64, strict=False)
        )
    return df


def remove_duplicates(df: pl.DataFrame) -> pl.DataFrame:
    """Remove exact duplicate rows from the DataFrame."""
    before = len(df)
    df = df.unique()
    after = len(df)
    logger.info("Removed %d duplicate rows.", before - after)
    return df


def remove_invalid_records(df: pl.DataFrame) -> pl.DataFrame:
    """Remove rows with null values in critical columns."""
    required_cols = ["Date", "Product Name", "Total Quantity"]
    existing_cols = [c for c in required_cols if c in df.columns]

    before = len(df)
    for col in existing_cols:
        df = df.filter(pl.col(col).is_not_null())
    after = len(df)
    logger.info("Removed %d invalid records.", before - after)
    return df


def add_age_bin(df: pl.DataFrame) -> pl.DataFrame:
    """
    Add a Month and Year column derived from the Date column.
    Used as time-based features for the forecasting model.
    """
    if "Date" not in df.columns:
        return df
    df = df.with_columns([
        pl.col("Date").dt.month().alias("Month"),
        pl.col("Date").dt.year().alias("Year"),
        pl.col("Date").dt.weekday().alias("DayOfWeek"),
    ])
    return df


def compute_most_frequent_price(
    df: pl.DataFrame,
    time_granularity: list[str],
) -> pl.DataFrame:
    """
    Compute the most frequently occurring Total Quantity per product
    at the given time granularity (e.g. ["Year", "Month"]).
    """
    missing = [c for c in time_granularity if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for grouping: {missing}")

    group_cols = ["Product Name"] + time_granularity
    mode_df = (
        df.group_by(group_cols)
        .agg(pl.col("Total Quantity").mode().first().alias("Modal Quantity"))
    )
    return df.join(mode_df, on=group_cols, how="left")


def detect_outliers_iqr(df: pl.DataFrame, column: str) -> pl.DataFrame:
    """
    Flag outliers in a numeric column using the IQR method.
    Adds an is_outlier boolean column to the DataFrame.
    """
    if column not in df.columns:
        return df

    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    df = df.with_columns(
        ((pl.col(column) < lower) | (pl.col(column) > upper)).alias("is_outlier")
    )
    outlier_count = df["is_outlier"].sum()
    logger.info("Detected %d outliers in %s.", outlier_count, column)
    return df


def main(
    source_bucket: str,
    destination_bucket: str,
    input_prefix: str = "",
    notify_email: str = "",
) -> None:
    """
    Run the full preprocessing pipeline on all files in the source bucket.

    Steps: load, type conversion, deduplication, invalid record removal,
    feature engineering, outlier detection, upload to destination bucket.
    """
    blobs = list_bucket_blobs(source_bucket, prefix=input_prefix)

    if not blobs:
        logger.info("No files found in bucket %s.", source_bucket)
        return

    for blob_name in blobs:
        logger.info("Preprocessing %s...", blob_name)
        try:
            df = load_bucket_data(source_bucket, blob_name)

            df = convert_feature_types(df)
            df = remove_duplicates(df)
            df = remove_invalid_records(df)
            df = add_age_bin(df)
            df = detect_outliers_iqr(df, "Total Quantity")

            output_blob = blob_name.replace("raw/", "processed/")
            upload_to_gcs(destination_bucket, output_blob, df)
            logger.info("Preprocessed file uploaded to %s.", output_blob)

            delete_blob_from_bucket(source_bucket, blob_name)

        except Exception as e:
            logger.error("Error preprocessing %s: %s", blob_name, e)
            if notify_email:
                send_anomaly_alert(f"Preprocessing failed for {blob_name}: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run preprocessing on GCS data.")
    parser.add_argument("--source-bucket", required=True)
    parser.add_argument("--destination-bucket", required=True)
    parser.add_argument("--prefix", default="")
    parser.add_argument("--notify-email", default="")
    args = parser.parse_args()

    main(
        source_bucket=args.source_bucket,
        destination_bucket=args.destination_bucket,
        input_prefix=args.prefix,
        notify_email=args.notify_email,
    )
    