# bootstrap/main.tf
# Creates the Terraform service account, assigns IAM roles,
# and provisions the Artifact Registry repository.
# Run this once before the main Infrastructure Terraform.

resource "google_service_account" "terraform_sa" {
  account_id   = "terraform-service-account"
  display_name = "Terraform Service Account"
  project      = var.project_id
}

resource "google_service_account_key" "terraform_sa_key" {
  service_account_id = google_service_account.terraform_sa.email
  key_algorithm      = "KEY_ALG_RSA_2048"
  private_key_type   = "TYPE_GOOGLE_CREDENTIALS_FILE"

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [private_key, public_key_data]
  }
}

resource "local_file" "sa_key_file" {
  content  = base64decode(trimspace(google_service_account_key.terraform_sa_key.private_key))
  filename = "${path.module}/sa_key.json"
}

resource "local_file" "sa_email_file" {
  content  = google_service_account.terraform_sa.email
  filename = "${path.module}/sa_email.txt"
}

locals {
  roles = [
    "roles/run.admin",
    "roles/eventarc.admin",
    "roles/logging.logWriter",
    "roles/storage.admin",
    "roles/storage.objectAdmin",
    "roles/aiplatform.admin",
    "roles/artifactregistry.admin",
    "roles/artifactregistry.reader",
    "roles/artifactregistry.repoAdmin",
    "roles/artifactregistry.writer",
    "roles/composer.admin",
    "roles/cloudfunctions.admin",
    "roles/cloudsql.admin",
    "roles/compute.admin",
    "roles/compute.serviceAgent",
    "roles/compute.storageAdmin",
    "roles/iam.serviceAccountCreator",
    "roles/resourcemanager.projectIamAdmin",
    "roles/secretmanager.admin",
    "roles/servicenetworking.networksAdmin",
    "roles/run.invoker",
    "roles/cloudsql.client",
    "roles/cloudscheduler.admin",
    "roles/monitoring.metricWriter",
    "roles/monitoring.admin",
    "roles/pubsub.admin",
    "roles/vpcaccess.admin",
  ]
}

resource "google_project_iam_member" "terraform_sa_roles" {
  for_each = toset(local.roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.terraform_sa.email}"
}

resource "google_artifact_registry_repository" "airflow_docker_repo" {
  repository_id = var.artifact_registry_name
  project       = var.project_id
  location      = "us-central1"
  format        = var.repo_format
  description   = "Docker repository for supply chain pipeline images"
}
