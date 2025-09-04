terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

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

  enforce_admins = false
  allows_deletions = false
  allows_force_pushes = false

  required_status_checks {
    strict = true
    contexts = ["ci"]
  }

  required_pull_request_reviews {
    required_approving_review_count = 1
  }
}

resource "github_repository_file" "readme" {
  repository = github_repository.vaga_linkedin.name
  branch     = "main"
  file       = "README.md"
  content    = file("../Readme.md")
  overwrite_on_create = true
}

# Adicionar mais recursos conforme necessário, como secrets para Actions
resource "github_actions_secret" "example" {
  repository      = github_repository.vaga_linkedin.name
  secret_name     = "EXAMPLE_SECRET"
  plaintext_value = "example_value"  # Substitua por valores reais
}
