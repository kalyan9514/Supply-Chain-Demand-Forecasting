"""
Data_Pipeline/scripts/pre_validation.py

Validates raw data from GCS before it enters the preprocessing pipeline.
Checks schema, column types, null values, and value ranges.
"""

import argparse
import polars as pl

try:
    from logger import logger
    from utils import (
        collect_validation_errors,
        delete_blob_from_bucket,
        list_bucket_blobs,
        load_bucket_data,
        send_email,
    )
except ImportError:
    from Data_Pipeline.scripts.logger import logger
    from Data_Pipeline.scripts.utils import (
        collect_validation_errors,
        delete_blob_from_bucket,
        list_bucket_blobs,
        load_bucket_data,
        send_email,
    )

PRE_VALIDATION_COLUMNS = [
    "Date",
    "Product Name",
    "Total Quantity",
]

NUMERIC_COLUMNS = ["Total Quantity"]
DATE_COLUMNS = ["Date"]


def validate_schema(df: pl.DataFrame) -> list[dict]:
    """Check that all required columns are present in the DataFrame."""
    errors = []
    for col in PRE_VALIDATION_COLUMNS:
        if col not in df.columns:
            errors.append({
                "index": -1,
                "error": f"Missing required column: {col}",
                "data": {},
            })
    return errors


def validate_nulls(df: pl.DataFrame) -> list[dict]:
    """Check for null values in required columns."""
    errors = []
    for col in PRE_VALIDATION_COLUMNS:
        if col not in df.columns:
            continue
        null_mask = df[col].is_null()
        if null_mask.any():
            errors.extend(
                collect_validation_errors(df, null_mask, f"Null value in {col}")
            )
    return errors


def validate_numeric_ranges(df: pl.DataFrame) -> list[dict]:
    """Check that numeric columns contain non-negative values."""
    errors = []
    for col in NUMERIC_COLUMNS:
        if col not in df.columns:
            continue
        negative_mask = df[col] < 0
        if negative_mask.any():
            errors.extend(
                collect_validation_errors(
                    df, negative_mask, f"Negative value in {col}"
                )
            )
    return errors


def validate_data(df: pl.DataFrame) -> list[dict]:
    """Run all pre-validation checks and return a combined list of errors."""
    errors = []
    errors.extend(validate_schema(df))
    errors.extend(validate_nulls(df))
    errors.extend(validate_numeric_ranges(df))
    return errors


def main(
    bucket_name: str,
    input_prefix: str = "",
    output_bucket: str = "",
    notify_email: str = "",
) -> None:
    """
    Run pre-validation on all files in a GCS bucket with the given prefix.

    Files that pass validation are moved to the output bucket.
    Files that fail are deleted and an alert email is sent.
    """
    blobs = list_bucket_blobs(bucket_name, prefix=input_prefix)

    if not blobs:
        logger.info("No files found in bucket %s with prefix %s.", bucket_name, input_prefix)
        return

    for blob_name in blobs:
        logger.info("Validating %s...", blob_name)
        try:
            df = load_bucket_data(bucket_name, blob_name)
            errors = validate_data(df)

            if errors:
                error_summary = "\n".join(
                    [f"Row {e['index']}: {e['error']}" for e in errors[:10]]
                )
                logger.error(
                    "Validation failed for %s. Errors:\n%s", blob_name, error_summary
                )
                if notify_email:
                    send_email(
                        subject=f"Pre-validation failed: {blob_name}",
                        body=error_summary,
                        to_email=notify_email,
                    )
                delete_blob_from_bucket(bucket_name, blob_name)
            else:
                logger.info("Validation passed for %s.", blob_name)

        except Exception as e:
            logger.error("Error processing %s: %s", blob_name, e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run pre-validation on GCS data.")
    parser.add_argument("--bucket", required=True, help="Source GCS bucket name")
    parser.add_argument("--prefix", default="", help="Blob name prefix filter")
    parser.add_argument("--output-bucket", default="", help="Output GCS bucket name")
    parser.add_argument("--notify-email", default="", help="Email for failure alerts")
    args = parser.parse_args()

    main(
        bucket_name=args.bucket,
        input_prefix=args.prefix,
        output_bucket=args.output_bucket,
        notify_email=args.notify_email,
    )
    