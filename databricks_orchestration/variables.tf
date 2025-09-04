variable "databricks_host" {}
variable "databricks_token" { sensitive = true }

variable "catalog_name" { default = "catalogo_dados" }
variable "schema_name"  { default = "bronze" }

variable "cred_name"    { default = "cred_s3" }
variable "extloc_name"  { default = "extloc_bronze" }
variable "s3_uri"       { default = "s3://meu-bucket/bronze/" }
variable "iam_role_arn" { default = "arn:aws:iam::123456789012:role/role-uc" }
