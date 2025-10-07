




# GCP services and IAM roles required for Cloud Run deployment

resource "google_project_service" "artifactregistry" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  service = "artifactregistry.googleapis.com"
}

resource "google_project_service" "run" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  service = "run.googleapis.com"
}

resource "google_project_service" "cloudbuild" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  service = "cloudbuild.googleapis.com"
}

resource "google_project_service" "cloudscheduler" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  service = "cloudscheduler.googleapis.com"
}

resource "google_project_service" "secretmanager" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  service = "secretmanager.googleapis.com"
}

resource "google_project_service" "storage" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  service = "storage.googleapis.com"
}

resource "google_project_iam_member" "artifactregistry_admin" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/artifactregistry.admin"
  member  = "user:${var.current_user_email}"
}

resource "google_project_iam_member" "run_admin" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/run.admin"
  member  = "user:${var.current_user_email}"
}

resource "google_project_iam_member" "cloudbuild_editor" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "user:${var.current_user_email}"
}

resource "google_project_iam_member" "cloudscheduler_admin" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/cloudscheduler.admin"
  member  = "user:${var.current_user_email}"
}

resource "google_project_iam_member" "secretmanager_admin" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/secretmanager.admin"
  member  = "user:${var.current_user_email}"
}

resource "google_project_iam_member" "storage_admin" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/storage.admin"
  member  = "user:${var.current_user_email}"
}

# ==================== SERVICE ACCOUNT IAM ROLES ====================
# Permissões para a service account usada no CI/CD (GitHub Actions)

resource "google_project_iam_member" "sa_run_admin" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${var.gcp_service_account_email}"
}

resource "google_project_iam_member" "sa_cloudbuild_builds_editor" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${var.gcp_service_account_email}"
}

resource "google_project_iam_member" "sa_iam_serviceAccountUser" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${var.gcp_service_account_email}"
}

resource "google_project_iam_member" "sa_artifactregistry_writer" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${var.gcp_service_account_email}"
}

resource "google_project_iam_member" "sa_storage_objectAdmin" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${var.gcp_service_account_email}"
}

resource "google_project_iam_member" "sa_secretmanager_accessor" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${var.gcp_service_account_email}"
}
