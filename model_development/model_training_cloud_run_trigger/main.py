"""
model_development/model_training_cloud_run_trigger/main.py

Flask service that triggers a Vertex AI custom training job.
Deployed as a Cloud Run service and called by Cloud Scheduler
on a weekly basis to retrain the LSTM model.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.cloud import aiplatform

load_dotenv()

app = Flask(__name__)
CORS(app)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
REGION = os.getenv("GCP_LOCATION", "us-central1")
BUCKET_URI = os.getenv("MODEL_TRAINING_BUCKET_URI", "")
IMAGE_URI = os.getenv("TRAINING_IMAGE_URI", "")
API_TOKEN = os.getenv("API_TOKEN", "")
SERVICE_ACCOUNT = os.getenv("SERVICE_ACCOUNT_EMAIL", "")


def verify_token(req) -> bool:
    """Check the API token from the request header."""
    return req.headers.get("token") == API_TOKEN


@app.route("/health", methods=["GET"])
def health():
    """Basic health check."""
    return jsonify({"status": "ok"}), 200


@app.route("/trigger-training", methods=["POST"])
def trigger_training():
    """
    Trigger a Vertex AI custom training job using the configured
    Docker image and GCS bucket.
    Returns the training job resource name.
    """
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    if not IMAGE_URI:
        return jsonify({"error": "TRAINING_IMAGE_URI not configured."}), 503

    try:
        aiplatform.init(project=PROJECT_ID, location=REGION)

        job = aiplatform.CustomContainerTrainingJob(
            display_name="lstm-demand-forecasting-training",
            container_uri=IMAGE_URI,
            staging_bucket=BUCKET_URI,
        )

        model = job.run(
            machine_type="n1-standard-4",
            accelerator_type="NVIDIA_TESLA_T4",
            accelerator_count=1,
            replica_count=1,
            service_account=SERVICE_ACCOUNT,
            sync=False,
        )

        return jsonify({
            "status": "training_triggered",
            "job_name": job.resource_name,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)