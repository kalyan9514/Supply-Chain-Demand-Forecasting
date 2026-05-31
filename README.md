# Supply-Chain-Demand-Forecasting

A production-grade LSTM demand forecasting system with a full MLOps pipeline on Google Cloud Platform. Combines deep learning forecasting with automated data validation, model retraining, drift detection, and fairness monitoring across product categories.

---

## Architecture

```
Excel Upload / Scheduled Trigger
        ↓
FastAPI Backend (Cloud Run)
        ↓
GCS Raw Data Bucket
        ↓
Airflow DAG (Compute Engine)
    ├── Pre-Validation
    ├── Preprocessing + Feature Engineering
    ├── Post-Validation
    └── DVC Data Versioning
        ↓
Cloud SQL (MySQL) — Processed Transactions
        ↓
Vertex AI Training Job
    ├── LSTM (production model)
    ├── XGBoost + Optuna + SHAP
    └── Debiased LSTM (fairness-aware)
        ↓
GCS Trained Model Bucket
        ↓
Model Serving (Cloud Run)
        ↓
Model Health Check (Cloud Run + Cloud Scheduler)
    ├── RMSE threshold monitoring
    └── KS-test drift detection
```

---

## Research Experiments

Model comparison results from experiments in `ML_Models/experiments/`:

| Model | Approach | Notes |
|-------|----------|-------|
| LSTM | Bidirectional LSTM with sequence modeling | Production model |
| Debiased LSTM | Fairness-aware training with SHAP explainability | Per-product fairness monitoring |
| XGBoost | Gradient boosting with Optuna hyperparameter search | Tabular baseline |
| DeepAR | Probabilistic forecasting with Gaussian NLL | Prediction intervals |
| SARIMA | Classical time series with auto_arima | Statistical baseline |

---

## Features

- LSTM demand forecasting trained on Cloud SQL transaction data via Vertex AI
- Fairness-aware debiased LSTM with per-product RMSE monitoring and bias correction
- XGBoost with Optuna hyperparameter optimization and SHAP feature importance
- DeepAR probabilistic forecasting with prediction intervals
- Airflow DAGs for automated pre-validation, preprocessing, post-validation, and DVC versioning
- FastAPI backend with file upload, prediction, validation, and scheduler endpoints
- Model health check service with RMSE threshold monitoring and KS-test drift detection
- Custom Cloud Monitoring metrics for model performance observability
- Full GCP infrastructure provisioned via Terraform
- GitHub Actions CI/CD for Docker image builds and infrastructure deployment
- Email alerting on pipeline failures and anomaly detection

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Forecasting Model | LSTM, XGBoost, DeepAR, SARIMA |
| ML Framework | TensorFlow, PyTorch, scikit-learn |
| Experiment Tracking | MLflow |
| Hyperparameter Optimization | Optuna |
| Explainability | SHAP |
| Pipeline Orchestration | Apache Airflow |
| Data Versioning | DVC |
| Backend API | FastAPI, Flask |
| Cloud Platform | GCP (Vertex AI, Cloud Run, Cloud SQL, GCS) |
| Infrastructure | Terraform |
| CI/CD | GitHub Actions |
| Containerization | Docker |

---

## Project Structure

```
├── Data_Generation/          # Synthetic demand and transaction data generators
├── Data_Pipeline/
│   ├── scripts/              # Pre-validation, preprocessing, post-validation, DVC versioning
│   └── tests/                # Unit tests for pipeline scripts
├── ML_Models/
│   ├── scripts/              # LSTM, XGBoost, debiased LSTM, health check
│   └── experiments/          # SARIMA and DeepAR baseline experiments
├── backend/                  # FastAPI backend for file upload and predictions
├── dags/                     # Airflow DAGs and docker-compose
├── model_development/
│   ├── model_serving_cloud_run/     # Flask model serving service
│   ├── model_training/              # Vertex AI training job container
│   └── model_training_cloud_run_trigger/  # Training trigger service
├── Infrastructure/           # Terraform for all GCP resources
├── bootstrap/                # Terraform for service account and Artifact Registry
├── scripts/                  # Docker build and deployment shell scripts
├── .github/workflows/        # CI/CD pipelines
├── DECISIONS.md              # Architecture decision records
└── .env.example              # Environment variable template
```

---

## Prerequisites

- Python 3.10+
- Docker Desktop
- GCP account with billing enabled
- gcloud CLI installed and authenticated
- Terraform >= 1.0.0

---

## Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/kalyan9514/Supply-Chain-Demand-Forecasting.git
cd Supply-Chain-Demand-Forecasting
```

**2. Create your .env file**
```bash
cp .env.example .env
```

**3. Fill in your credentials in .env**
```bash
GCP_PROJECT_ID=your_project_id
GCP_SERVICE_ACCOUNT_KEY=your_key_json
MYSQL_HOST=your_cloud_sql_ip
...
```

**4. Bootstrap GCP infrastructure**
```bash
cd bootstrap
terraform init
terraform apply
```

**5. Deploy full infrastructure**
```bash
cd Infrastructure
terraform init
terraform apply
```

**6. Deploy Airflow**
```bash
bash scripts/setup_vm.sh
bash scripts/deploy_airflow.sh
```

**7. Run the backend locally**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| GCP_PROJECT_ID | GCP project ID |
| GCP_SERVICE_ACCOUNT_KEY | Service account key JSON |
| GCP_LOCATION | GCP region (default: us-central1) |
| MYSQL_HOST | Cloud SQL instance IP |
| MYSQL_USER | Database user |
| MYSQL_PASSWORD | Database password |
| MYSQL_DATABASE | Database name |
| API_TOKEN | Token for Cloud Run service auth |
| SMTP_EMAIL | Email for pipeline alerts |
| SMTP_PASSWORD | SMTP password for email alerts |
| MODEL_NAME | Trained model filename |
| TRAINED_MODEL_BUCKET_URI | GCS bucket for trained models |

---

## Services

| Service | Description |
|---------|-------------|
| FastAPI Backend | File upload, predictions, validation |
| Model Serving | LSTM inference endpoint |
| Model Health Check | RMSE and drift monitoring |
| Training Trigger | Vertex AI job launcher |
| Airflow | Pipeline orchestration |

---

## Contact

[LinkedIn — Kalyan Kumar](https://www.linkedin.com/in/kalyan-kumar-8170a111b/)