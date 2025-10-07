# Agent Chat Infrastructure Configuration

# Secret Scope para credenciais do Agent Chat
resource "databricks_secret_scope" "agent_chat" {
  name                     = "vaga_linkedin_agent_chat"
  initial_manage_principal = "users"
}

# Secrets do Telegram Bot
resource "databricks_secret" "telegram_bot_token" {
  key          = "telegram_bot_token"
  string_value = var.telegram_bot_token
  scope        = databricks_secret_scope.agent_chat.name
}

resource "databricks_secret" "telegram_chat_id" {
  key          = "telegram_chat_id"
  string_value = var.telegram_chat_id
  scope        = databricks_secret_scope.agent_chat.name
}

resource "databricks_secret" "telegram_secret_token" {
  key          = "telegram_secret_token"
  string_value = var.telegram_secret_token != "" ? var.telegram_secret_token : "webhook_secret_${random_string.webhook_secret.result}"
  scope        = databricks_secret_scope.agent_chat.name
}

resource "databricks_secret" "databricks_pat" {
  key          = "databricks_pat"
  string_value = var.databricks_token
  scope        = databricks_secret_scope.agent_chat.name
}

# Random secret para webhook se não fornecido
resource "random_string" "webhook_secret" {
  length  = 32
  special = true
}

# Job Principal: LinkedIn Pipeline V4 (Bronze → Silver → Gold → Agent Chat)
resource "databricks_job" "linkedin_pipeline_v4" {
  name = "linkedin-pipeline-v4"

  # Free Edition: Serverless-only environment (no cluster config needed)

  # Tarefa 1: Executar Pipeline DLT (Bronze → Silver → Gold)
  task {
    task_key                  = "dlt-pipeline-execution"
    timeout_seconds           = 3600
    max_retries               = 1
    min_retry_interval_millis = 60000

    notebook_task {
      notebook_path = "/Shared/linkedin_pipeline_runner_notebook"
      base_parameters = {
        "mode"        = "transform"
        "environment" = "production"
      }
    }
  }

  # Tarefa 2: Agent Chat Notification (dependente do DLT)  
  task {
    task_key = "agent-chat-notification"
    depends_on {
      task_key = "dlt-pipeline-execution"
    }
    timeout_seconds           = 1800
    max_retries               = 2
    min_retry_interval_millis = 30000

    notebook_task {
      notebook_path = "/Shared/linkedin_pipeline_runner_notebook"
      base_parameters = {
        "mode"     = "chat"
        "telegram" = "enabled"
      }
    }
  }

  # Agendamento: 08h30, 12h30, 21h30 (seg-sex)
  schedule {
    quartz_cron_expression = "0 30 8,12,21 ? * MON-FRI"
    timezone_id            = "America/Sao_Paulo"
    pause_status           = "UNPAUSED"
  }

  timeout_seconds     = 14400 # 4 horas total
  max_concurrent_runs = 1

  email_notifications {
    on_failure = [var.notification_email]
    on_success = [var.notification_email]
  }

  tags = {
    "environment" = var.environment
    "project"     = "vaga_linkedin"
    "pipeline"    = "v4"
    "component"   = "extraction_transformation"
  }
}

# Notebook do Agent Chat removido - incompatível com Community Edition paths

# Outputs
output "linkedin_pipeline_job_id" {
  description = "ID do job LinkedIn Pipeline V4"
  value       = databricks_job.linkedin_pipeline_v4.id
}

output "linkedin_pipeline_job_url" {
  description = "URL do job LinkedIn Pipeline V4"
  value       = databricks_job.linkedin_pipeline_v4.url
}

output "telegram_secret_scope" {
  description = "Nome do secret scope do Telegram"
  value       = databricks_secret_scope.agent_chat.name
}

output "webhook_secret_token" {
  description = "Token secreto para validação do webhook"
  value       = random_string.webhook_secret.result
  sensitive   = true
}
