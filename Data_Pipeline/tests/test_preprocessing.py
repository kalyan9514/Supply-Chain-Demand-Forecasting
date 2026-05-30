"""
Data_Pipeline/tests/test_preprocessing.py

Unit tests for the preprocessing pipeline.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../scripts"))

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from unittest.mock import MagicMock, patch
from preprocessing import (
    convert_feature_types,
    remove_duplicates,
    remove_invalid_records,
    add_age_bin,
    detect_outliers_iqr,
)


def make_sample_df() -> pl.DataFrame:
    """Create a sample DataFrame for testing."""
    return pl.DataFrame({
        "Date": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "Product Name": ["beef", "chicken", "pork"],
        "Total Quantity": [100.0, 200.0, 300.0],
    })


def test_remove_duplicates():
    df = pl.DataFrame({
        "Date": ["2023-01-01", "2023-01-01", "2023-01-02"],
        "Product Name": ["beef", "beef", "chicken"],
        "Total Quantity": [100.0, 100.0, 200.0],
    })
    result = remove_duplicates(df)
    assert len(result) == 2


def test_remove_invalid_records_drops_nulls():
    df = pl.DataFrame({
        "Date": ["2023-01-01", None, "2023-01-03"],
        "Product Name": ["beef", "chicken", "pork"],
        "Total Quantity": [100.0, 200.0, 300.0],
    })
    result = remove_invalid_records(df)
    assert len(result) == 2


def test_add_age_bin_adds_columns():
    df = make_sample_df()
    df = df.with_columns(pl.col("Date").cast(pl.Date))
    result = add_age_bin(df)
    assert "Month" in result.columns
    assert "Year" in result.columns
    assert "DayOfWeek" in result.columns


def test_detect_outliers_iqr_flags_outliers():
    df = pl.DataFrame({
        "Total Quantity": [100.0, 110.0, 105.0, 108.0, 10000.0],
    })
    result = detect_outliers_iqr(df, "Total Quantity")
    assert "is_outlier" in result.columns
    assert result["is_outlier"].sum() >= 1


def test_convert_feature_types_casts_correctly():
    df = pl.DataFrame({
        "Date": ["2023-01-01", "2023-01-02"],
        "Product Name": ["beef", "chicken"],
        "Total Quantity": ["100.0", "200.0"],
    })
    result = convert_feature_types(df)
    assert result["Total Quantity"].dtype == pl.Float64
    