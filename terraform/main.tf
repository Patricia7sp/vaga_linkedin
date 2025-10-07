# Terraform configuration moved to databricks_dlt.tf to avoid duplicates

provider "github" {
  token = var.github_token
}

resource "github_repository" "vaga_linkedin" {
  name        = "vaga_linkedin"
  description = "Projeto de coleta e processamento de vagas do LinkedIn usando agentes IA"
  visibility  = "public"
  auto_init   = true

  topics = ["data-pipeline", "linkedin", "ai-agents", "pyspark", "terraform"]
}

resource "github_branch_protection" "main" {
  repository_id = github_repository.vaga_linkedin.node_id
  pattern       = "main"

  enforce_admins      = false
  allows_deletions    = false
  allows_force_pushes = false

  required_status_checks {
    strict   = true
    contexts = ["ci"]
  }

  required_pull_request_reviews {
    required_approving_review_count = 1
  }
}

resource "github_repository_file" "readme" {
  repository          = github_repository.vaga_linkedin.name
  branch              = "main"
  file                = "README.md"
  content             = file("../Readme.md")
  overwrite_on_create = true
}

# GitHub Actions Secrets para CI/CD e Deploy
resource "github_actions_secret" "databricks_host" {
  repository      = github_repository.vaga_linkedin.name
  secret_name     = "DATABRICKS_HOST"
  plaintext_value = var.databricks_host
}

resource "github_actions_secret" "databricks_token" {
  repository      = github_repository.vaga_linkedin.name
  secret_name     = "DATABRICKS_TOKEN"
  plaintext_value = var.databricks_token
}

resource "github_actions_secret" "gcp_credentials" {
  repository      = github_repository.vaga_linkedin.name
  secret_name     = "GCP_SERVICE_ACCOUNT_KEY"
  plaintext_value = var.gcp_service_account_key
}

resource "github_actions_secret" "linkedin_username" {
  repository      = github_repository.vaga_linkedin.name
  secret_name     = "LINKEDIN_USERNAME"
  plaintext_value = var.linkedin_username
}

resource "github_actions_secret" "linkedin_password" {
  repository      = github_repository.vaga_linkedin.name
  secret_name     = "LINKEDIN_PASSWORD"
  plaintext_value = var.linkedin_password
}

resource "github_actions_secret" "kafka_bootstrap_servers" {
  repository      = github_repository.vaga_linkedin.name
  secret_name     = "KAFKA_BOOTSTRAP_SERVERS"
  plaintext_value = var.kafka_bootstrap_servers
}

resource "github_actions_secret" "aws_access_key_id" {
  repository      = github_repository.vaga_linkedin.name
  secret_name     = "AWS_ACCESS_KEY_ID"
  plaintext_value = var.aws_access_key_id
}

resource "github_actions_secret" "aws_secret_access_key" {
  repository      = github_repository.vaga_linkedin.name
  secret_name     = "AWS_SECRET_ACCESS_KEY"
  plaintext_value = var.aws_secret_access_key
}
