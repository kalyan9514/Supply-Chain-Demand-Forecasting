# Infrastructure/sql_database.tf
# Provisions a Cloud SQL MySQL instance for storing
# transaction data and model predictions.

resource "google_sql_database_instance" "instance" {
  name             = "supply-chain-sql"
  region           = var.region
  database_version = "MYSQL_8_0"
  deletion_protection = false

  settings {
    tier = "db-f1-micro"

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.airflow_vpc.self_link
    }

    backup_configuration {
      enabled            = true
      binary_log_enabled = true
    }
  }

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_compute_global_address.private_ip_range,
    google_compute_subnetwork.airflow_subnet,
  ]
}

resource "google_sql_database" "database" {
  name     = var.mysql_database
  instance = google_sql_database_instance.instance.name

  depends_on = [google_sql_database_instance.instance]
}

resource "google_sql_user" "user" {
  name     = var.mysql_user
  instance = google_sql_database_instance.instance.name
  password = var.mysql_password
  host     = "%"

  depends_on = [google_sql_database.database]
}