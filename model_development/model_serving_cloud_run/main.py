"""
model_development/model_serving_cloud_run/main.py

Flask service that loads the trained LSTM model from Vertex AI
Model Registry and serves predictions via a REST API.
Deployed as a Cloud Run service.
"""

import os
import json

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.cloud import aiplatform, storage
from tensorflow.keras.models import load_model

try:
    from logger import logger
except ImportError:
    from Data_Pipeline.scripts.logger import logger

load_dotenv()

app = Flask(__name__)
CORS(app)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
REGION = os.getenv("GCP_LOCATION", "us-central1")
TRAINED_MODEL_BUCKET = os.getenv("TRAINED_MODEL_BUCKET_URI", "").replace("gs://", "")
MODEL_NAME = os.getenv("MODEL_NAME", "lstm_model.keras")
API_TOKEN = os.getenv("API_TOKEN", "")

_model = None


def load_model_from_gcs() -> object:
    """Download and load the LSTM model from GCS."""
    global _model
    if _model is not None:
        return _model

    client = storage.Client()
    bucket = client.bucket(TRAINED_MODEL_BUCKET)
    blob = bucket.blob(f"models/{MODEL_NAME}")
    local_path = f"/tmp/{MODEL_NAME}"
    blob.download_to_filename(local_path)
    _model = load_model(local_path)
    logger.info("Model loaded from GCS: %s", MODEL_NAME)
    return _model


def verify_token(req) -> bool:
    """Check the API token from the request header."""
    return req.headers.get("token") == API_TOKEN


@app.route("/health", methods=["GET"])
def health():
    """Basic health check."""
    return jsonify({"status": "ok"}), 200


@app.route("/predict", methods=["POST"])
def predict():
    """
    Generate demand forecasts for the next n days.
    Expects a JSON body with a list of recent demand values.
    """
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        recent_values = data.get("values", [])

        if len(recent_values) < 30:
            return jsonify({"error": "At least 30 historical values are required."}), 400

        model = load_model_from_gcs()
        input_array = np.array(recent_values[-30:], dtype=np.float32).reshape(1, 30, 1)
        predictions = model.predict(input_array)

        return jsonify({
            "predictions": predictions[0].tolist(),
            "forecast_horizon": len(predictions[0]),
        }), 200

    except Exception as e:
        logger.error("Prediction error: %s", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
    