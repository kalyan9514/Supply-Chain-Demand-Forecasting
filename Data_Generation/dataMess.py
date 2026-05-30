"""
Data_Generation/dataMess.py

Intentionally introduces noise, missing values, duplicates,
outliers, and inconsistencies into a clean dataset.
Used to test the robustness of the data validation pipeline.
"""

import random
import numpy as np
import pandas as pd


def mess_up_data(input_file: str, output_file: str) -> None:
    """
    Load a dataset and introduce various data quality issues.

    Issues introduced:
    - Missing values in random cells
    - Inconsistent date formats
    - Outliers in numeric columns
    - Duplicate rows
    - Logical inconsistencies (negative quantities)
    - Consecutive row deletions
    """
    df = pd.read_csv(input_file, parse_dates=["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    # Introduce missing values
    num_missing = int(len(df) * 0.05)
    for _ in range(num_missing):
        row = random.randint(0, len(df) - 1)
        col = random.choice(df.columns.tolist())
        df.at[row, col] = np.nan

    # Inconsistent date formats
    num_date_issues = int(len(df) * 0.02)
    for _ in range(num_date_issues):
        row = random.randint(0, len(df) - 1)
        if pd.notna(df.at[row, "Date"]):
            df.at[row, "Date"] = df.at[row, "Date"].strftime("%d/%m/%Y")

    # Outliers in Total Quantity
    num_outliers = int(len(df) * 0.02)
    for _ in range(num_outliers):
        row = random.randint(0, len(df) - 1)
        df.at[row, "Total Quantity"] = random.uniform(10000, 50000)

    # Negative quantities (logical inconsistency)
    num_negative = int(len(df) * 0.01)
    for _ in range(num_negative):
        row = random.randint(0, len(df) - 1)
        df.at[row, "Total Quantity"] = -abs(df.at[row, "Total Quantity"])

    # Duplicate rows
    num_duplicates = int(len(df) * 0.03)
    duplicate_indices = random.sample(range(len(df)), num_duplicates)
    duplicates = df.iloc[duplicate_indices]
    df = pd.concat([df, duplicates], ignore_index=True)

    # Consecutive row deletions
    start_delete = random.randint(0, len(df) - 20)
    df = df.drop(index=range(start_delete, start_delete + 10)).reset_index(drop=True)

    df.to_csv(output_file, index=False)
    print(f"Messy dataset saved to {output_file} with {len(df)} rows.")


if __name__ == "__main__":
    mess_up_data(
        input_file="data/commodity_demand.csv",
        output_file="data/commodity_demand_messy.csv",
    )
    