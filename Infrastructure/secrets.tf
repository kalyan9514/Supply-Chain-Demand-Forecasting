# Infrastructure/secrets.tf
# Secret Manager secrets for sensitive configuration values.
# Secrets are referenced by Cloud Run services at runtime.

resource "google_secret_manager_secret" "mysql_password" {
  secret_id = "mysql_password"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "mysql_password_version" {
  secret      = google_secret_manager_secret.mysql_password.id
  secret_data = var.mysql_password
}

resource "google_secret_manager_secret" "api_token" {
  secret_id = "api_token"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "api_token_version" {
  secret      = google_secret_manager_secret.api_token.id
  secret_data = var.api_token
}
