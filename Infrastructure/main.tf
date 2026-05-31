# Infrastructure/main.tf
# Primary entry point for GCP infrastructure provisioning.
# Orchestrates all resource modules for the supply chain platform.

resource "google_compute_network" "airflow_vpc" {
  name                    = var.network_name
  project                 = var.project_id
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "airflow_subnet" {
  name          = "${var.network_name}-subnet"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.airflow_vpc.self_link
  ip_cidr_range = "10.0.0.0/24"
}

resource "google_compute_global_address" "private_ip_range" {
  name          = "private-ip-range"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.airflow_vpc.self_link
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.airflow_vpc.self_link
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}