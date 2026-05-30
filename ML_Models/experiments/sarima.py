"""
ML_Models/experiments/sarima.py

SARIMA-based demand forecasting experiment.
Compares classical time series forecasting against the LSTM baseline.
Results are logged with MLflow for comparison.
"""

import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima import auto_arima

from model_training_utils import get_latest_data_from_cloud_sql

try:
    from logger import logger
except ImportError:
    from Data_Pipeline.scripts.logger import logger


def preprocess_data(df: pd.DataFrame, product: str, years: int = 2) -> pd.DataFrame:
    """
    Filter and aggregate data for a single product.
    Returns a daily time series indexed by date.
    """
    df["date"] = pd.to_datetime(df["date"])
    latest_date = df["date"].max()
    cutoff = latest_date - pd.DateOffset(years=years)
    df = df[df["date"] >= cutoff]
    df = df[df["product_name"] == product]
    df = df.groupby("date")["total_quantity"].sum().to_frame()
    df = df.asfreq("D", fill_value=0)
    return df


def fit_sarima(series: pd.Series) -> SARIMAX:
    """
    Fit a SARIMA model using auto_arima to find the best order automatically.
    Returns the fitted SARIMAX model.
    """
    logger.info("Running auto_arima to find best SARIMA order...")
    auto_model = auto_arima(
        series,
        seasonal=True,
        m=7,
        stepwise=True,
        suppress_warnings=True,
        error_action="ignore",
    )
    order = auto_model.order
    seasonal_order = auto_model.seasonal_order
    logger.info("Best order: %s, seasonal order: %s", order, seasonal_order)

    model = SARIMAX(series, order=order, seasonal_order=seasonal_order)
    return model.fit(disp=False)


def evaluate(
    fitted_model,
    test_series: pd.Series,
) -> dict:
    """Generate forecasts and compute evaluation metrics."""
    forecast = fitted_model.forecast(steps=len(test_series))
    actual = test_series.values
    predicted = forecast.values

    mae = mean_absolute_error(actual, predicted)
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    mape = float(np.mean(np.abs((actual - predicted) / (actual + 1e-8))) * 100)

    return {"mae": mae, "rmse": rmse, "mape": mape}


def run_experiment(product: str = "beef", years: int = 2) -> None:
    """
    Run a full SARIMA experiment for a single product.
    Logs parameters and metrics to MLflow.
    """
    logger.info("Starting SARIMA experiment for product: %s", product)
    df = get_latest_data_from_cloud_sql(days=years * 365)
    series_df = preprocess_data(df, product=product, years=years)
    series = series_df["total_quantity"]

    split = int(len(series) * 0.8)
    train_series = series.iloc[:split]
    test_series = series.iloc[split:]

    mlflow.set_experiment("SARIMA_Demand_Forecasting")
    with mlflow.start_run(run_name=f"SARIMA_{product}"):
        fitted = fit_sarima(train_series)
        metrics = evaluate(fitted, test_series)

        mlflow.log_param("product", product)
        mlflow.log_param("years_of_data", years)
        mlflow.log_metrics(metrics)

        logger.info(
            "SARIMA results for %s: RMSE=%.4f, MAPE=%.2f%%",
            product, metrics["rmse"], metrics["mape"],
        )


if __name__ == "__main__":
    run_experiment(product="beef", years=2)