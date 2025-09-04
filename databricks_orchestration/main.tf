# --- Unity Catalog: catálogo e schema ---
resource "databricks_catalog" "sales" {
  name         = var.catalog_name
  comment      = "Catálogo provisionado via Terraform"
  force_destroy = true
}

resource "databricks_schema" "bronze" {
  name         = var.schema_name
  catalog_name = databricks_catalog.sales.name
  comment      = "Schema bronze"
}

# --- Credencial + External Location (ex.: AWS) ---
resource "databricks_storage_credential" "s3" {
  name = var.cred_name
  aws_iam_role {
    role_arn = var.iam_role_arn
  }
}

resource "databricks_external_location" "bronze" {
  name            = var.extloc_name
  url             = var.s3_uri # ex: s3://meu-bucket/bronze/
  credential_name = databricks_storage_credential.s3.name
  read_only       = false
}

# --- Grants no Catálogo ---
# Use databricks_grant para adições pontuais, ou databricks_grants para "state total" do objeto.
resource "databricks_grants" "catalog_sales" {
  catalog = databricks_catalog.sales.name

  grant {
    principal  = "data_scientists"
    privileges = ["USE_CATALOG", "BROWSE", "CREATE_SCHEMA"]
  }
  grant {
    principal  = "data_readers"
    privileges = ["USE_CATALOG", "BROWSE"]
  }
}

# --- Grants no Schema ---
resource "databricks_grants" "schema_bronze" {
  schema = "${databricks_catalog.sales.name}.${databricks_schema.bronze.name}"

  grant {
    principal  = "data_scientists"
    privileges = ["USE_SCHEMA", "CREATE_TABLE", "CREATE_VIEW", "CREATE_FUNCTION", "MODIFY", "SELECT"]
  }
  grant {
    principal  = "data_readers"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}
