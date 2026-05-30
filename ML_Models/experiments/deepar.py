"""
ML_Models/experiments/deepar.py

DeepAR-based probabilistic demand forecasting experiment.
Uses a PyTorch LSTM with Gaussian likelihood to produce
prediction intervals alongside point forecasts.
Results are logged with MLflow for comparison against
the LSTM and SARIMA baselines.
"""

import math

import mlflow
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.metrics import mean_squared_error
from torch.utils.data import DataLoader, Dataset

from model_training_utils import (
    engineer_features,
    get_latest_data_from_cloud_sql,
)

try:
    from logger import logger
except ImportError:
    from Data_Pipeline.scripts.logger import logger

# Configuration
SEQUENCE_LENGTH = 30
FORECAST_HORIZON = 7
HIDDEN_SIZE = 64
NUM_LAYERS = 2
DROPOUT = 0.1
BATCH_SIZE = 32
EPOCHS = 30
LEARNING_RATE = 0.001


class DemandDataset(Dataset):
    """PyTorch Dataset for demand forecasting sequences."""

    def __init__(
        self,
        data: np.ndarray,
        sequence_length: int,
        forecast_horizon: int,
    ):
        self.X = []
        self.y = []
        for i in range(len(data) - sequence_length - forecast_horizon + 1):
            self.X.append(data[i:i + sequence_length])
            self.y.append(data[i + sequence_length:i + sequence_length + forecast_horizon])
        self.X = torch.tensor(np.array(self.X), dtype=torch.float32)
        self.y = torch.tensor(np.array(self.y), dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class DeepARModel(nn.Module):
    """
    LSTM model with Gaussian likelihood output for probabilistic forecasting.
    Outputs both mean and log variance for each forecast step.
    """

    def __init__(
        self,
        input_size: int = 1,
        hidden_size: int = HIDDEN_SIZE,
        num_layers: int = NUM_LAYERS,
        forecast_horizon: int = FORECAST_HORIZON,
        dropout: float = DROPOUT,
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.mu_head = nn.Linear(hidden_size, forecast_horizon)
        self.log_var_head = nn.Linear(hidden_size, forecast_horizon)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        out, _ = self.lstm(x)
        last_hidden = out[:, -1, :]
        mu = self.mu_head(last_hidden)
        log_var = self.log_var_head(last_hidden)
        return mu, log_var


def gaussian_nll_loss(
    mu: torch.Tensor,
    log_var: torch.Tensor,
    target: torch.Tensor,
) -> torch.Tensor:
    """Gaussian negative log-likelihood loss for probabilistic training."""
    var = torch.exp(log_var) + 1e-6
    loss = 0.5 * (log_var + (target - mu) ** 2 / var)
    return loss.mean()


def train(df: pd.DataFrame) -> dict:
    """
    Train the DeepAR model and log results to MLflow.
    Returns evaluation metrics and the trained model.
    """
    df = engineer_features(df)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[["total_quantity"]])

    split = int(len(scaled) * 0.8)
    train_data = scaled[:split]
    test_data = scaled[split:]

    train_dataset = DemandDataset(train_data, SEQUENCE_LENGTH, FORECAST_HORIZON)
    test_dataset = DemandDataset(test_data, SEQUENCE_LENGTH, FORECAST_HORIZON)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = DeepARModel().to(device)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    mlflow.set_experiment("DeepAR_Demand_Forecasting")
    with mlflow.start_run():
        mlflow.log_params({
            "sequence_length": SEQUENCE_LENGTH,
            "forecast_horizon": FORECAST_HORIZON,
            "hidden_size": HIDDEN_SIZE,
            "num_layers": NUM_LAYERS,
            "dropout": DROPOUT,
            "batch_size": BATCH_SIZE,
            "epochs": EPOCHS,
            "learning_rate": LEARNING_RATE,
        })

        for epoch in range(EPOCHS):
            model.train()
            total_loss = 0.0
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device)
                optimizer.zero_grad()
                mu, log_var = model(X_batch)
                loss = gaussian_nll_loss(mu, log_var, y_batch)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            if (epoch + 1) % 5 == 0:
                logger.info(
                    "Epoch %d/%d, Loss: %.4f",
                    epoch + 1, EPOCHS, total_loss / len(train_loader),
                )

        model.eval()
        all_preds, all_targets = [], []
        with torch.no_grad():
            for X_batch, y_batch in test_loader:
                X_batch = X_batch.to(device)
                mu, _ = model(X_batch)
                all_preds.append(mu.cpu().numpy())
                all_targets.append(y_batch.numpy())

        preds = np.concatenate(all_preds).flatten()
        targets = np.concatenate(all_targets).flatten()

        rmse = math.sqrt(mean_squared_error(targets, preds))
        mape = float(np.mean(np.abs((targets - preds) / (targets + 1e-8))) * 100)

        mlflow.log_metrics({"rmse": rmse, "mape": mape})
        logger.info("DeepAR training complete. RMSE: %.4f, MAPE: %.2f%%", rmse, mape)

    return {"model": model, "rmse": rmse, "mape": mape}


if __name__ == "__main__":
    df = get_latest_data_from_cloud_sql(days=730)
    results = train(df)
    