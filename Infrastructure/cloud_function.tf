# Infrastructure/cloud_function.tf
# Cloud Function that moves fully processed data files
# from GCS into the Cloud SQL database.

resource "google_storage_bucket_object" "cloud_function_zip" {
  name   = "cloud_function_source.zip"
  bucket = google_storage_bucket.buckets["fully-processed-data"].name
  source = "../Cloudrun_Function/GCS_TO_SQL.zip"
}

resource "google_cloudfunctions_function" "gcs_to_sql" {
  name        = "gcs-to-sql"
  description = "Moves processed data from GCS to Cloud SQL"
  runtime     = "python310"
  project     = var.project_id
  region      = var.region

  available_memory_mb   = 512
  source_archive_bucket = google_storage_bucket.buckets["fully-processed-data"].name
  source_archive_object = google_storage_bucket_object.cloud_function_zip.name
  trigger_http          = true
  entry_point           = "gcs_to_sql"

  environment_variables = {
    GCP_PROJECT_ID  = var.project_id
    MYSQL_DATABASE  = var.mysql_database
    MYSQL_USER      = var.mysql_user
  }

  service_account_email = var.service_account_email
}
