variable "github_token" {
  description = "GitHub personal access token with repo permissions"
  type        = string
  sensitive   = true
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

# GCP Configuration
variable "gcp_service_account_key" {
  description = "GCP service account JSON key (base64 encoded)"
  type        = string
  sensitive   = true
}

# LinkedIn Credentials
variable "linkedin_username" {
  description = "LinkedIn username for scraping"
  type        = string
  sensitive   = true
}

variable "linkedin_password" {
  description = "LinkedIn password for scraping"
  type        = string
  sensitive   = true
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
