# Infrastructure/gcs_buckets.tf
# Creates GCS buckets for raw data, processed data,
# trained models, and Terraform state.

resource "google_storage_bucket" "buckets" {
  for_each      = var.bucket_names
  name          = each.value
  location      = var.region
  project       = var.project_id
  force_destroy = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}