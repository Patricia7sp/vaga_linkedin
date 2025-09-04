terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.60" # use a estável mais recente
    }
  }
}

provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}
