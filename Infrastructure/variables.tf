variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "GCP zone"
  default     = "us-central1-a"
}

variable "gcp_service_account_key" {
  type        = string
  description = "GCP service account key in JSON format"
  sensitive   = true
}

variable "network_name" {
  type        = string
  description = "VPC network name"
  default     = "airflow-vpc"
}

variable "machine_type" {
  type        = string
  description = "Compute Engine machine type for Airflow VM"
  default     = "e2-standard-4"
}

variable "mysql_database" {
  type        = string
  description = "Cloud SQL database name"
}

variable "mysql_user" {
  type        = string
  description = "Cloud SQL database user"
}

variable "mysql_password" {
  type        = string
  description = "Cloud SQL database password"
  sensitive   = true
}

variable "api_token" {
  type        = string
  description = "API token for Cloud Run services"
  sensitive   = true
}

variable "service_account_email" {
  type        = string
  description = "Service account email for Cloud Run and Vertex AI"
}

variable "bucket_names" {
  type        = map(string)
  description = "Map of GCS bucket names to create"
  default     = {}
}

variable "artifact_registry_name" {
  type        = string
  description = "Artifact Registry repository name"
  default     = "airflow-docker-image"
}