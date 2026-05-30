"""
Data_Generation/dataGenerator.py

Generates synthetic supply chain demand data influenced by
real NASDAQ stock prices, weekly patterns, and random demand shocks.
Used to create realistic training data for the forecasting models.
"""

import os
import random
import time
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

# Hyperparameters
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
BASE_DEMAND_RANGE = (100, 500)
NOISE_STD_RANGE = (5, 15)
STOCK_INFLUENCE_STRENGTH = 0.5
WEEKLY_VARIATION = True
RANDOM_SHOCK_PROB = 0.05
RANDOM_SHOCK_RANGE = (50, 200)

COMMODITIES = [
    "beef", "chicken", "pork", "salmon", "tuna",
    "rice", "wheat", "corn", "soybeans", "coffee",
    "sugar", "cocoa", "cotton", "rubber", "palm_oil",
]

NASDAQ_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "TSLA", "NVDA", "PYPL", "INTC", "AMD",
    "CSCO", "ADBE", "NFLX", "QCOM", "TXN",
]


def fetch_stock_data(symbol: str, start: str, end: str) -> pd.Series:
    """Fetch daily closing prices for a NASDAQ symbol."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end)
        return df["Close"]
    except Exception as e:
        print(f"Warning: Could not fetch {symbol}: {e}")
        return pd.Series(dtype=float)


def generate_demand(
    dates: pd.DatetimeIndex,
    stock_prices: pd.Series,
    base_demand: int,
    noise_std: float,
) -> list[float]:
    """
    Generate synthetic daily demand values for a single product.

    Combines a base demand level with stock price influence,
    weekly seasonality, and random demand shocks.
    """
    demand = []
    stock_normalized = (
        (stock_prices - stock_prices.min())
        / (stock_prices.max() - stock_prices.min() + 1e-8)
    )

    for i, date in enumerate(dates):
        stock_influence = 0.0
        if date in stock_normalized.index:
            stock_influence = (
                stock_normalized.get(date, 0) * STOCK_INFLUENCE_STRENGTH * base_demand
            )

        weekly_factor = 1.0
        if WEEKLY_VARIATION:
            weekly_factor = 1.0 + 0.1 * np.sin(2 * np.pi * date.dayofweek / 7)

        shock = 0.0
        if random.random() < RANDOM_SHOCK_PROB:
            shock = random.uniform(*RANDOM_SHOCK_RANGE)

        noise = np.random.normal(0, noise_std)
        value = base_demand + stock_influence + shock + noise
        value *= weekly_factor
        demand.append(max(0, round(value, 2)))

    return demand


def generate_dataset(output_path: str = "data/commodity_demand.csv") -> pd.DataFrame:
    """
    Generate the full synthetic demand dataset and save to CSV.

    Returns the generated DataFrame.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    dates = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
    records = []

    for i, commodity in enumerate(COMMODITIES):
        symbol = NASDAQ_SYMBOLS[i % len(NASDAQ_SYMBOLS)]
        print(f"Generating data for {commodity} using {symbol}...")

        stock_prices = fetch_stock_data(symbol, START_DATE, END_DATE)
        time.sleep(0.5)

        base_demand = random.randint(*BASE_DEMAND_RANGE)
        noise_std = random.uniform(*NOISE_STD_RANGE)
        demand_values = generate_demand(dates, stock_prices, base_demand, noise_std)

        for date, demand in zip(dates, demand_values):
            records.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Product Name": commodity,
                "Total Quantity": demand,
            })

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"Dataset saved to {output_path} with {len(df)} records.")
    return df


if __name__ == "__main__":
    df = generate_dataset()
    print(df.head())