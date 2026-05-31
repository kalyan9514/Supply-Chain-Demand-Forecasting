variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "us-central1"
}

variable "gcp_service_account_key" {
  description = "Bootstrap service account key in JSON format"
  type        = string
  sensitive   = true
}

variable "artifact_registry_name" {
  description = "Name of the Artifact Registry repository"
  type        = string
  default     = "airflow-docker-image"
}

variable "repo_format" {
  description = "Repository format. Use DOCKER for container images."
  type        = string
  default     = "DOCKER"
}
