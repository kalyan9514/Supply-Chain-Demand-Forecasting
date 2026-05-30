"""
ML_Models/scripts/model_xgboost.py

XGBoost-based demand forecasting model with Optuna hyperparameter
optimization and SHAP-based explainability.
Trains on Cloud SQL data, logs with MLflow, and uploads artifacts to GCS.
"""

import os
import math

import mlflow
import numpy as np
import optuna
import pandas as pd
import shap
from dotenv import load_dotenv
from google.cloud import aiplatform
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

from model_training_utils import (
    engineer_features,
    get_latest_data_from_cloud_sql,
    upload_pickle_to_gcs,
)

try:
    from logger import logger
except ImportError:
    from Data_Pipeline.scripts.logger import logger

load_dotenv()

TRAINED_MODEL_BUCKET = os.getenv("TRAINED_MODEL_BUCKET_URI", "").replace("gs://", "")
N_TRIALS = 30
TEST_SIZE = 0.2
RANDOM_STATE = 42


def objective(trial: optuna.Trial, X_train, y_train, X_val, y_val) -> float:
    """Optuna objective function for XGBoost hyperparameter optimization."""
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 1e-4, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    }
    model = XGBRegressor(**params)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    preds = model.predict(X_val)
    return math.sqrt(mean_squared_error(y_val, preds))


def compute_shap_values(
    model: XGBRegressor,
    X: np.ndarray,
    feature_names: list[str],
) -> dict:
    """Compute SHAP feature importance values for the trained model."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance = dict(zip(feature_names, mean_abs_shap.tolist()))
    sorted_importance = dict(
        sorted(importance.items(), key=lambda x: x[1], reverse=True)
    )
    logger.info("Top SHAP features: %s", list(sorted_importance.keys())[:5])
    return sorted_importance


def train(df: pd.DataFrame) -> dict:
    """
    Train the XGBoost model with Optuna hyperparameter optimization.
    Logs parameters, metrics, and SHAP values to MLflow.
    Returns a dict with the trained model and evaluation metrics.
    """
    df = engineer_features(df)

    feature_cols = [
        c for c in df.columns
        if c not in ["date", "product_name", "total_quantity"]
    ]
    X = df[feature_cols].values
    y = df["total_quantity"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.1, random_state=RANDOM_STATE
    )

    mlflow.set_experiment("XGBoost_Demand_Forecasting")
    with mlflow.start_run():
        study = optuna.create_study(direction="minimize")
        study.optimize(
            lambda trial: objective(trial, X_train, y_train, X_val, y_val),
            n_trials=N_TRIALS,
        )

        best_params = study.best_params
        best_params["random_state"] = RANDOM_STATE
        best_params["n_jobs"] = -1

        mlflow.log_params(best_params)
        logger.info("Best hyperparameters: %s", best_params)

        model = XGBRegressor(**best_params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

        preds = model.predict(X_test)
        rmse = math.sqrt(mean_squared_error(y_test, preds))
        mape = float(np.mean(np.abs((y_test - preds) / (y_test + 1e-8))) * 100)

        mlflow.log_metrics({"rmse": rmse, "mape": mape})
        logger.info("XGBoost training complete. RMSE: %.4f, MAPE: %.2f%%", rmse, mape)

        shap_importance = compute_shap_values(model, X_test, feature_cols)
        mlflow.log_dict(shap_importance, "shap_importance.json")

    return {
        "model": model,
        "rmse": rmse,
        "mape": mape,
        "shap_importance": shap_importance,
        "feature_cols": feature_cols,
    }


def main() -> None:
    """Fetch data, train XGBoost, and upload the model artifact to GCS."""
    logger.info("Fetching training data from Cloud SQL...")
    df = get_latest_data_from_cloud_sql(days=730)

    logger.info("Starting XGBoost training...")
    results = train(df)

    model_path = "xgboost_model.pkl"
    import pickle
    with open(model_path, "wb") as f:
        pickle.dump(results["model"], f)

    if TRAINED_MODEL_BUCKET:
        upload_pickle_to_gcs(
            local_pickle_path=model_path,
            bucket_name=TRAINED_MODEL_BUCKET,
            destination_blob_name="models/xgboost_model.pkl",
        )
        logger.info("XGBoost model uploaded to GCS.")


if __name__ == "__main__":
    main()
    