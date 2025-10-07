variable "github_token" {
  description = "GitHub personal access token with repo permissions"
  type        = string
  sensitive   = true
  default     = ""
}

# Databricks Configuration
variable "databricks_host" {
  description = "Databricks workspace URL"
  type        = string
  sensitive   = true
}

variable "databricks_token" {
  description = "Databricks personal access token"
  type        = string
  sensitive   = true
}

# Free Edition não precisa de cluster ID (serverless-only)
# variable "databricks_existing_cluster_id" {
#   description = "Existing interactive cluster ID (not used in Free Edition)"
#   type        = string  
#   default     = ""
# }

# GCP Configuration
variable "gcp_service_account_key" {
  description = "GCP service account JSON key (base64 encoded)"
  type        = string
  sensitive   = true
  default     = ""
}

# LinkedIn Credentials
variable "linkedin_username" {
  description = "LinkedIn username for scraping"
  type        = string
  sensitive   = true
  default     = ""
}

variable "linkedin_password" {
  description = "LinkedIn password for scraping"
  type        = string
  sensitive   = true
  default     = ""
}

# Kafka Configuration
variable "kafka_bootstrap_servers" {
  description = "Kafka bootstrap servers list"
  type        = string
  default     = "localhost:9092"
}

# AWS Configuration (for future Unity Catalog integration)
variable "aws_access_key_id" {
  description = "AWS Access Key ID for S3 integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "aws_secret_access_key" {
  description = "AWS Secret Access Key for S3 integration"
  type        = string
  sensitive   = true
  default     = ""
}

# Additional variables for Unity Catalog and GCP
variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "manage_gcp_resources" {
  description = "Set to true to allow Terraform to manage GCP services and IAM bindings"
  type        = bool
  default     = false
}

variable "schemas_ready" {
  description = "Defina como true após os pipelines criarem os schemas Bronze/Silver/Gold"
  type        = bool
  default     = true
}

variable "databricks_account_id" {
  description = "Databricks Account ID"
  type        = string
}

variable "current_user_email" {
  description = "Current user email for Unity Catalog permissions"
  type        = string
}

variable "gcp_service_account_email" {
  description = "GCP service account email for CI/CD deployments"
  type        = string
  default     = "linkedin-scraper@vaga-linkedin.iam.gserviceaccount.com"
}

variable "catalog_name" {
  description = "Unity Catalog name"
  type        = string
  default     = "vagas_linkedin"
}

variable "domains" {
  description = "Domain list for DLT pipelines"
  type        = list(string)
  default     = ["data_engineer", "data_analytics", "digital_analytics"]
}

# Agent Chat Variables
variable "telegram_bot_token" {
  description = "Telegram Bot Token from BotFather"
  type        = string
  sensitive   = true
}

variable "telegram_chat_id" {
  description = "Telegram Chat ID for notifications"
  type        = string
  sensitive   = true
}

variable "telegram_secret_token" {
  description = "Secret token for webhook validation"
  type        = string
  sensitive   = true
  default     = ""
}

variable "databricks_username" {
  description = "Databricks username for Repos path"
  type        = string
  default     = "patricia7sp"
}

variable "databricks_warehouse_id" {
  description = "Databricks SQL Warehouse ID"
  type        = string
  default     = "ab43ca87b28a5a1d"
}

variable "notification_email" {
  description = "Email for job notifications"
  type        = string
  default     = "paty7sp@gmail.com"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}
