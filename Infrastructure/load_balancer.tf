# Infrastructure/load_balancer.tf
# HTTP load balancer that distributes traffic to the
# Airflow managed instance group.

resource "google_compute_health_check" "http_health_check" {
  name    = "airflow-health-check"
  project = var.project_id

  check_interval_sec = 10
  timeout_sec        = 5

  http_health_check {
    port         = 8080
    request_path = "/api/v1/health"
  }
}

resource "google_compute_backend_service" "airflow_backend" {
  name                  = "airflow-backend-service"
  project               = var.project_id
  protocol              = "HTTP"
  port_name             = "http"
  load_balancing_scheme = "EXTERNAL"
  health_checks         = [google_compute_health_check.http_health_check.id]

  backend {
    group = google_compute_region_instance_group_manager.airflow_mig.instance_group
  }
}

resource "google_compute_url_map" "airflow_url_map" {
  name            = "airflow-url-map"
  project         = var.project_id
  default_service = google_compute_backend_service.airflow_backend.id
}

resource "google_compute_target_http_proxy" "airflow_http_proxy" {
  name    = "airflow-http-proxy"
  project = var.project_id
  url_map = google_compute_url_map.airflow_url_map.id
}

resource "google_compute_global_forwarding_rule" "airflow_forwarding_rule" {
  name                  = "airflow-forwarding-rule"
  project               = var.project_id
  target                = google_compute_target_http_proxy.airflow_http_proxy.id
  port_range            = "80"
  load_balancing_scheme = "EXTERNAL"
}
