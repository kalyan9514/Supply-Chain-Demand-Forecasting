"""
Data_Pipeline/scripts/post_validation.py

Validates preprocessed data after the preprocessing pipeline completes.
Checks column types, numeric stats, and data consistency before
the data is handed off to model training.
"""

import argparse

import polars as pl

try:
    from logger import logger
    from utils import (
        collect_validation_errors,
        list_bucket_blobs,
        load_bucket_data,
        send_anomaly_alert,
    )
except ImportError:
    from Data_Pipeline.scripts.logger import logger
    from Data_Pipeline.scripts.utils import (
        collect_validation_errors,
        list_bucket_blobs,
        load_bucket_data,
        send_anomaly_alert,
    )

POST_VALIDATION_COLUMNS = {
    "Date": pl.Date,
    "Product Name": pl.Utf8,
    "Total Quantity": pl.Float64,
    "Month": pl.Int8,
    "Year": pl.Int32,
    "DayOfWeek": pl.Int8,
}


def check_column_types(df: pl.DataFrame) -> list[dict]:
    """Check that each expected column exists and has the correct dtype."""
    errors = []
    for col, expected_type in POST_VALIDATION_COLUMNS.items():
        if col not in df.columns:
            errors.append({
                "index": -1,
                "error": f"Missing expected column after preprocessing: {col}",
                "data": {},
            })
        elif df[col].dtype != expected_type:
            errors.append({
                "index": -1,
                "error": (
                    f"Column {col} has type {df[col].dtype}, "
                    f"expected {expected_type}"
                ),
                "data": {},
            })
    return errors


def generate_numeric_stats(df: pl.DataFrame) -> dict:
    """Generate basic descriptive statistics for numeric columns."""
    stats = {}
    numeric_cols = [
        col for col in df.columns
        if df[col].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32)
    ]
    for col in numeric_cols:
        stats[col] = {
            "mean": df[col].mean(),
            "std": df[col].std(),
            "min": df[col].min(),
            "max": df[col].max(),
            "null_count": df[col].null_count(),
        }
    return stats


def validate_data(df: pl.DataFrame) -> list[dict]:
    """Run all post-validation checks and return a combined list of errors."""
    errors = []
    errors.extend(check_column_types(df))

    if "Total Quantity" in df.columns:
        negative_mask = df["Total Quantity"] < 0
        if negative_mask.any():
            errors.extend(
                collect_validation_errors(
                    df,
                    negative_mask,
                    "Negative Total Quantity after preprocessing",
                )
            )

    return errors


def main(
    bucket_name: str,
    input_prefix: str = "",
    notify_email: str = "",
) -> None:
    """
    Run post-validation on all preprocessed files in the given GCS bucket.

    Logs stats for passing files and sends alerts for failing files.
    """
    blobs = list_bucket_blobs(bucket_name, prefix=input_prefix)

    if not blobs:
        logger.info("No files found in bucket %s with prefix %s.", bucket_name, input_prefix)
        return

    for blob_name in blobs:
        logger.info("Post-validating %s...", blob_name)
        try:
            df = load_bucket_data(bucket_name, blob_name)
            errors = validate_data(df)

            if errors:
                error_summary = "\n".join(
                    [f"Row {e['index']}: {e['error']}" for e in errors[:10]]
                )
                logger.error(
                    "Post-validation failed for %s:\n%s", blob_name, error_summary
                )
                if notify_email:
                    send_anomaly_alert(
                        f"Post-validation failed for {blob_name}:\n{error_summary}"
                    )
            else:
                stats = generate_numeric_stats(df)
                logger.info(
                    "Post-validation passed for %s. Stats: %s", blob_name, stats
                )

        except Exception as e:
            logger.error("Error post-validating %s: %s", blob_name, e)
            if notify_email:
                send_anomaly_alert(f"Post-validation error for {blob_name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run post-validation on preprocessed GCS data.")
    parser.add_argument("--bucket", required=True, help="GCS bucket with preprocessed data")
    parser.add_argument("--prefix", default="", help="Blob name prefix filter")
    parser.add_argument("--notify-email", default="", help="Email for failure alerts")
    args = parser.parse_args()

    main(
        bucket_name=args.bucket,
        input_prefix=args.prefix,
        notify_email=args.notify_email,
    )