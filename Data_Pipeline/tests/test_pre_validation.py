"""
Data_Pipeline/tests/test_pre_validation.py

Unit tests for the pre-validation pipeline.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../scripts"))

import polars as pl
import pytest
from unittest.mock import MagicMock, patch
from pre_validation import (
    validate_schema,
    validate_nulls,
    validate_numeric_ranges,
    validate_data,
)


def make_valid_df() -> pl.DataFrame:
    """Create a valid sample DataFrame for testing."""
    return pl.DataFrame({
        "Date": ["2023-01-01", "2023-01-02"],
        "Product Name": ["beef", "chicken"],
        "Total Quantity": [100.0, 200.0],
    })


def test_validate_schema_passes_with_valid_df():
    df = make_valid_df()
    errors = validate_schema(df)
    assert len(errors) == 0


def test_validate_schema_fails_with_missing_column():
    df = pl.DataFrame({
        "Date": ["2023-01-01"],
        "Product Name": ["beef"],
    })
    errors = validate_schema(df)
    assert any("Total Quantity" in e["error"] for e in errors)


def test_validate_nulls_passes_with_no_nulls():
    df = make_valid_df()
    errors = validate_nulls(df)
    assert len(errors) == 0


def test_validate_nulls_fails_with_null_values():
    df = pl.DataFrame({
        "Date": ["2023-01-01", None],
        "Product Name": ["beef", "chicken"],
        "Total Quantity": [100.0, 200.0],
    })
    errors = validate_nulls(df)
    assert len(errors) > 0


def test_validate_numeric_ranges_passes_with_positive_values():
    df = make_valid_df()
    errors = validate_numeric_ranges(df)
    assert len(errors) == 0


def test_validate_numeric_ranges_fails_with_negative_values():
    df = pl.DataFrame({
        "Date": ["2023-01-01", "2023-01-02"],
        "Product Name": ["beef", "chicken"],
        "Total Quantity": [100.0, -50.0],
    })
    errors = validate_numeric_ranges(df)
    assert len(errors) > 0


def test_validate_data_returns_no_errors_for_valid_df():
    df = make_valid_df()
    errors = validate_data(df)
    assert len(errors) == 0
    