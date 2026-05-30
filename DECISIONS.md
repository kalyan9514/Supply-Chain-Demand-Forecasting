# Architecture Decision Records

This document explains the key design decisions made in the
Supply Chain Demand Forecasting project.

---

## 1. LSTM as the primary forecasting model

**Decision:** LSTM is the production model deployed via Vertex AI.

**Why:** Supply chain demand data is sequential with seasonality, trends,
and sudden demand shocks. LSTM captures these temporal dependencies better
than classical models. DeepAR, SARIMA, and XGBoost are available in
ML_Models/experiments/ for comparison but are not deployed to production.

---

## 2. Airflow for pipeline orchestration

**Decision:** Apache Airflow runs on a GCP Compute Engine VM via Docker Compose.

**Why:** The pipeline has multiple dependent stages: data ingestion,
pre-validation, preprocessing, post-validation, and model retraining.
Airflow DAGs make each stage independently schedulable, retriable,
and observable without custom orchestration code.

---

## 3. Vertex AI for model training and serving

**Decision:** Model training and serving run on GCP Vertex AI via Cloud Run triggers.

**Why:** Vertex AI provides managed infrastructure for GPU training,
experiment tracking, model versioning, and scalable serving endpoints.
This avoids managing training infrastructure manually.

---

## 4. DVC for data versioning

**Decision:** DVC tracks versions of datasets stored in GCS buckets.

**Why:** Raw and processed datasets change with every ingestion cycle.
DVC provides reproducibility by linking each model version to the exact
dataset version it was trained on.

---

## 5. Terraform for infrastructure as code

**Decision:** All GCP resources are provisioned via Terraform in the
Infrastructure/ and bootstrap/ directories.

**Why:** Manual GCP resource creation is error-prone and not reproducible.
Terraform ensures the entire infrastructure can be torn down and recreated
consistently across environments.

---

## 6. Separate Cloud Run services per concern

**Decision:** Model training, model serving, training trigger, and health
check each run as independent Cloud Run services.

**Why:** Separating concerns means each service can be scaled, updated,
and monitored independently. A health check failure does not affect
the serving endpoint.

---

## 7. Fairness-aware LSTM training

**Decision:** The debiased LSTM pipeline includes per-product fairness
monitoring and bias correction via SHAP values.

**Why:** A model that forecasts accurately on average but poorly for
specific product categories causes real operational harm. Fairness
metrics ensure consistent performance across all product types.

---

## 8. No frontend in this repository

**Decision:** The Next.js dashboard is excluded from this repo.

**Why:** The frontend is a separate deployable concern. This repo focuses
on the data pipeline, ML models, backend API, and infrastructure.
The backend exposes REST endpoints that any frontend can consume.