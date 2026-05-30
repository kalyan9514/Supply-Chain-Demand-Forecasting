"""
ML_Models/scripts/model_lstm.py

LSTM-based demand forecasting model.
Trains on historical transaction data from Cloud SQL,
logs experiments with MLflow, and uploads the trained
model artifact to GCS.
"""

import os
import logging
import math

import numpy as np
import pandas as pd
import tensorflow as tf
from dotenv import load_dotenv
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam
import mlflow
import mlflow.tensorflow

from model_training_utils import (
    engineer_features,
    get_latest_data_from_cloud_sql,
    upload_artifact_to_gcs,
)

try:
    from logger import logger
except ImportError:
    from Data_Pipeline.scripts.logger import logger

load_dotenv()

# Configuration
SEQUENCE_LENGTH = 30
FORECAST_HORIZON = 7
BATCH_SIZE = 32
EPOCHS = 50
LEARNING_RATE = 0.001
LSTM_UNITS = [128, 64]
DROPOUT_RATE = 0.2
MODEL_NAME = os.getenv("MODEL_NAME", "lstm_model.keras")
TRAINED_MODEL_BUCKET = os.getenv("TRAINED_MODEL_BUCKET_URI", "").replace("gs://", "")


def build_sequences(
    data: np.ndarray,
    sequence_length: int,
    forecast_horizon: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build input sequences and target values for LSTM training.
    Each sequence of length sequence_length predicts the next
    forecast_horizon values.
    """
    X, y = [], []
    for i in range(len(data) - sequence_length - forecast_horizon + 1):
        X.append(data[i:i + sequence_length])
        y.append(data[i + sequence_length:i + sequence_length + forecast_horizon])
    return np.array(X), np.array(y)


def build_model(
    input_shape: tuple,
    forecast_horizon: int,
    lstm_units: list[int],
    dropout_rate: float,
    learning_rate: float,
) -> tf.keras.Model:
    """Build and compile the LSTM model."""
    model = Sequential([
        LSTM(lstm_units[0], return_sequences=True, input_shape=input_shape),
        Dropout(dropout_rate),
        LSTM(lstm_units[1], return_sequences=False),
        Dropout(dropout_rate),
        Dense(32, activation="relu"),
        Dense(forecast_horizon),
    ])
    model.compile(
        optimizer=Adam(learning_rate=learning_rate),
        loss="mse",
        metrics=["mae"],
    )
    return model


def train(df: pd.DataFrame) -> dict:
    """
    Train the LSTM model on the given DataFrame.
    Logs parameters and metrics to MLflow.
    Returns a dict with the trained model and evaluation metrics.
    """
    df = engineer_features(df)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[["total_quantity"]])

    X, y = build_sequences(scaled, SEQUENCE_LENGTH, FORECAST_HORIZON)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    model = build_model(
        input_shape=(SEQUENCE_LENGTH, 1),
        forecast_horizon=FORECAST_HORIZON,
        lstm_units=LSTM_UNITS,
        dropout_rate=DROPOUT_RATE,
        learning_rate=LEARNING_RATE,
    )

    callbacks = [
        EarlyStopping(patience=5, restore_best_weights=True),
        ModelCheckpoint(MODEL_NAME, save_best_only=True),
    ]

    mlflow.set_experiment("LSTM_Demand_Forecasting")
    with mlflow.start_run():
        mlflow.log_params({
            "sequence_length": SEQUENCE_LENGTH,
            "forecast_horizon": FORECAST_HORIZON,
            "lstm_units": LSTM_UNITS,
            "dropout_rate": DROPOUT_RATE,
            "learning_rate": LEARNING_RATE,
            "batch_size": BATCH_SIZE,
            "epochs": EPOCHS,
        })

        history = model.fit(
            X_train, y_train,
            validation_data=(X_test, y_test),
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            callbacks=callbacks,
            verbose=1,
        )

        y_pred = model.predict(X_test)
        rmse = math.sqrt(mean_squared_error(y_test.flatten(), y_pred.flatten()))
        train_loss = min(history.history["loss"])
        test_loss = min(history.history["val_loss"])

        mlflow.log_metrics({
            "rmse": rmse,
            "train_loss": train_loss,
            "test_loss": test_loss,
        })
        mlflow.tensorflow.log_model(model, "lstm_model")

        logger.info("LSTM training complete. RMSE: %.4f", rmse)

    return {
        "model": model,
        "scaler": scaler,
        "rmse": rmse,
        "train_loss": train_loss,
        "test_loss": test_loss,
    }


def main() -> None:
    """Fetch data, train the LSTM model, and upload the artifact to GCS."""
    logger.info("Fetching training data from Cloud SQL...")
    df = get_latest_data_from_cloud_sql(days=730)

    logger.info("Starting LSTM training...")
    results = train(df)

    if TRAINED_MODEL_BUCKET:
        upload_artifact_to_gcs(
            local_path=MODEL_NAME,
            bucket_name=TRAINED_MODEL_BUCKET,
            destination_blob=f"models/{MODEL_NAME}",
        )
        logger.info("Model uploaded to GCS.")


if __name__ == "__main__":
    main()
    