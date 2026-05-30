"""
Data_Generation/transactionGenerator.py

Generates realistic retail transaction records with inflation-adjusted
pricing, store locations, producer IDs, and realistic timestamps.
Used to populate the Cloud SQL database for pipeline testing.
"""

import os
import uuid
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from tqdm import tqdm

# Constants
SAVE_DIR = "data/transaction/"
DEMAND_FILEPATH = "data/commodity_demand.csv"

STORE_LOCATIONS = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
]

PAYMENT_METHODS = ["Credit Card", "Debit Card", "Cash", "Mobile Payment"]

BASE_PRICES = {
    "beef": 12.50, "chicken": 6.00, "pork": 8.00, "salmon": 15.00,
    "tuna": 10.00, "rice": 2.50, "wheat": 1.80, "corn": 2.00,
    "soybeans": 3.00, "coffee": 9.00, "sugar": 1.50, "cocoa": 5.00,
    "cotton": 4.00, "rubber": 3.50, "palm_oil": 4.50,
}

INFLATION_RATE = 0.03


def apply_inflation(base_price: float, date: datetime) -> float:
    """Adjust price for inflation relative to a base date of 2019-01-01."""
    base_date = datetime(2019, 1, 1)
    years_elapsed = (date - base_date).days / 365.25
    return round(base_price * ((1 + INFLATION_RATE) ** years_elapsed), 2)


def generate_transactions(
    demand_df: pd.DataFrame,
    output_path: str,
) -> pd.DataFrame:
    """
    Generate transaction records from a demand DataFrame.

    Each row in the demand DataFrame produces one or more transaction
    records with randomized store, payment method, and producer details.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    records = []

    for _, row in tqdm(demand_df.iterrows(), total=len(demand_df)):
        date = pd.to_datetime(row["Date"])
        product = row["Product Name"]
        quantity = max(1, int(row["Total Quantity"]))

        base_price = BASE_PRICES.get(product, 5.00)
        unit_price = apply_inflation(base_price, date)
        total_price = round(unit_price * quantity, 2)

        records.append({
            "transaction_id": str(uuid.uuid4()),
            "date": date.strftime("%Y-%m-%d"),
            "product_name": product,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
            "store_location": np.random.choice(STORE_LOCATIONS),
            "payment_method": np.random.choice(PAYMENT_METHODS),
            "producer_id": f"PROD_{np.random.randint(1000, 9999)}",
        })

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"Transaction dataset saved to {output_path} with {len(df)} records.")
    return df


if __name__ == "__main__":
    demand_df = pd.read_csv(DEMAND_FILEPATH)
    generate_transactions(
        demand_df=demand_df,
        output_path=os.path.join(SAVE_DIR, "transactions.csv"),
    )