# Infrastructure/instance_template.tf
# VM instance template for the Airflow Compute Engine deployment.

resource "google_compute_instance_template" "airflow_template" {
  name_prefix  = "airflow-instance-"
  project      = var.project_id
  machine_type = var.machine_type

  disk {
    boot         = true
    auto_delete  = true
    source_image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"
    disk_size_gb = 50
  }

  network_interface {
    network    = google_compute_network.airflow_vpc.self_link
    subnetwork = google_compute_subnetwork.airflow_subnet.self_link
  }

  service_account {
    email  = var.service_account_email
    scopes = ["cloud-platform"]
  }

  tags = ["airflow-server"]

  metadata = {
    enable-oslogin = "TRUE"
  }

  lifecycle {
    create_before_destroy = true
  }
}
