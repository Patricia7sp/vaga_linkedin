terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.29"
    }
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}

provider "google" {
  credentials = file(var.gcp_service_account_key)
  project     = var.gcp_project_id
  region      = var.gcp_region
}

# All variables are now declared in variables.tf

# DLT Pipelines for each domain - using serverless compute
resource "databricks_pipeline" "vagas_linkedin_dlt" {
  for_each = toset(var.domains)

  name    = "dlt_vagas_linkedin_${each.key}"
  catalog = data.databricks_catalog.vagas_linkedin.name

  configuration = {
    "pipelines.autoOptimize.managed"    = "true"
    "pipelines.autoOptimize.zOrderCols" = "extract_date"
    "pipelines.trigger.availableNow"    = "true"
  }

  # Use serverless compute (required in this workspace)
  serverless = true

  library {
    notebook {
      path = "/Shared/${each.key}_dlt_transformation"
    }
  }

  # Target deve ser somente o nome do schema (catalog já definido acima)
  # Exemplo: data_engineer_dlt
  target      = "${each.key}_dlt"
  continuous  = false
  development = false

  depends_on = [
    databricks_notebook.dlt_notebooks
  ]
}

# Unity Catalog Configuration - reference existing catalog created via UI
# With Default Storage enabled, catalog must be created manually via UI
data "databricks_catalog" "vagas_linkedin" {
  name = var.catalog_name
}

# Grant ADMIN permissions to current user on catalog
resource "databricks_grants" "catalog_admin" {
  catalog = data.databricks_catalog.vagas_linkedin.name
  grant {
    principal  = var.current_user_email
    privileges = ["ALL_PRIVILEGES"]
  }
}

locals {
  schemas_should_exist = var.schemas_ready
}

data "databricks_schema" "raw_schemas" {
  for_each = local.schemas_should_exist ? toset(var.domains) : toset([])

  name = "${data.databricks_catalog.vagas_linkedin.name}.${each.key}_raw"
}

data "databricks_schema" "bronze_schemas" {
  for_each = local.schemas_should_exist ? toset(var.domains) : toset([])

  name = "${data.databricks_catalog.vagas_linkedin.name}.${each.key}_dlt"
}

data "databricks_schema" "silver_schemas" {
  for_each = local.schemas_should_exist ? toset(var.domains) : toset([])

  name = "${data.databricks_catalog.vagas_linkedin.name}.${each.key}_dlt"
}

data "databricks_schema" "gold_schemas" {
  for_each = local.schemas_should_exist ? toset(var.domains) : toset([])

  name = "${data.databricks_catalog.vagas_linkedin.name}.${each.key}_dlt"
}

# Reference existing Unity Catalog volumes
data "databricks_volume" "linkedin_data_volumes" {
  for_each = toset(var.domains)

  name = "${data.databricks_catalog.vagas_linkedin.name}.${each.key}_raw.linkedin_data_volume"
}

resource "databricks_grants" "schema_admin" {
  for_each = local.schemas_should_exist ? toset(var.domains) : toset([])

  schema = "${data.databricks_catalog.vagas_linkedin.name}.${each.key}_raw"
  grant {
    principal  = var.current_user_email
    privileges = ["ALL_PRIVILEGES"]
  }

  depends_on = [data.databricks_schema.raw_schemas]
}

resource "databricks_grants" "dlt_schema_admin" {
  for_each = local.schemas_should_exist ? toset(var.domains) : toset([])

  schema = "${data.databricks_catalog.vagas_linkedin.name}.${each.key}_dlt"
  grant {
    principal  = var.current_user_email
    privileges = ["ALL_PRIVILEGES"]
  }

  depends_on = [data.databricks_schema.bronze_schemas]
}

# Grant READ/WRITE VOLUME permissions
resource "databricks_grants" "volume_admin" {
  for_each = toset(var.domains)

  volume = "${data.databricks_catalog.vagas_linkedin.name}.${each.key}_raw.linkedin_data_volume"
  grant {
    principal  = var.current_user_email
    privileges = ["READ_VOLUME", "WRITE_VOLUME"]
  }

  depends_on = [data.databricks_volume.linkedin_data_volumes]
}

# GCP IAM Configuration - MANAGED MANUALLY
# Due to organizational policies limiting Terraform GCP access, 
# all GCP resources are created and managed manually via gcloud CLI:
#
# Service Account: databricks-dlt-service@vaga-linkedin.iam.gserviceaccount.com
# Roles granted:
# - roles/storage.admin (for GCS access)
# - roles/bigquery.dataEditor (for BigQuery write access)  
# - roles/bigquery.jobUser (for BigQuery job execution)
# 
# Service account key: ../databricks-sa-key.json
# Created with: gcloud iam service-accounts keys create databricks-sa-key.json

# Upload DLT notebooks to Databricks workspace
resource "databricks_notebook" "dlt_notebooks" {
  for_each = toset(var.domains)

  path     = "/Shared/${each.key}_dlt_transformation"
  language = "PYTHON"

  # Use content_base64 for force re-upload when content changes
  content_base64 = filebase64("../transform_output/dlt_${each.key}_transformation.py")
}

# Outputs
output "pipeline_ids" {
  description = "DLT Pipeline IDs"
  value = {
    for domain, pipeline in databricks_pipeline.vagas_linkedin_dlt :
    domain => pipeline.id
  }
}

output "pipeline_urls" {
  description = "DLT Pipeline URLs"
  value = {
    for domain, pipeline in databricks_pipeline.vagas_linkedin_dlt :
    domain => pipeline.url
  }
}

output "unity_catalog_info" {
  description = "Unity Catalog configuration"
  value = {
    catalog_name = data.databricks_catalog.vagas_linkedin.name
    schemas = {
      for domain in var.domains : domain => {
        raw    = "${data.databricks_catalog.vagas_linkedin.name}.${domain}_raw"
        bronze = "${data.databricks_catalog.vagas_linkedin.name}.${domain}_bronze"
        silver = "${data.databricks_catalog.vagas_linkedin.name}.${domain}_silver"
        gold   = "${data.databricks_catalog.vagas_linkedin.name}.${domain}_gold"
      }
    }
    volumes = {
      for domain in var.domains : domain => "${data.databricks_catalog.vagas_linkedin.name}.${domain}_raw.linkedin_data_volume"
    }
  }
}

output "gcp_service_account_info" {
  description = "GCP Service Account for Databricks (manually managed)"
  value = {
    email    = "databricks-dlt-service@vaga-linkedin.iam.gserviceaccount.com"
    key_file = "../databricks-sa-key.json"
    roles    = ["roles/storage.admin", "roles/bigquery.dataEditor", "roles/bigquery.jobUser"]
  }
}

output "gcp_setup_instructions" {
  description = "Instructions to enable required GCP APIs"
  value = {
    cloud_resource_manager_api = "https://console.developers.google.com/apis/api/cloudresourcemanager.googleapis.com/overview?project=${var.gcp_project_id}"
    service_usage_api          = "https://console.developers.google.com/apis/api/serviceusage.googleapis.com/overview?project=${var.gcp_project_id}"
    iam_api                    = "https://console.developers.google.com/apis/api/iam.googleapis.com/overview?project=${var.gcp_project_id}"
  }
}
