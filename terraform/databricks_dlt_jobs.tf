# ============================================================================
# DLT Pipeline Jobs - One job per pipeline (Free Edition compatible)
# ============================================================================
# 
# PROBLEMA RESOLVIDO:
# - Free Edition limita a 1 pipeline DLT ativo por vez
# - Solução: 3 jobs independentes com horários espaçados
# 
# CADA JOB:
# - Executa o mesmo notebook: /Shared/linkedin_pipeline_runner_notebook
# - Passa parâmetro diferente: pipeline = "data_engineer" | "data_analytics" | "digital_analytics"
# - Horários espaçados 30min para evitar concorrência
# ============================================================================

locals {
  # Configuração dos 3 jobs DLT
  dlt_jobs = {
    data_engineer = {
      name        = "dlt-data-engineer-pipeline"
      description = "Executa pipeline DLT Data Engineer (Bronze→Silver→Gold)"
      pipeline    = "data_engineer"
      # Segunda a Sexta: 08:30, 12:30, 21:30 (Horário de Brasília)
      cron        = "0 30 8,12,21 ? * MON-FRI"
      tags = {
        pipeline = "data_engineer"
        type     = "dlt"
        domain   = "data_engineer"
      }
    }
    
    data_analytics = {
      name        = "dlt-data-analytics-pipeline"
      description = "Executa pipeline DLT Data Analytics (Bronze→Silver→Gold)"
      pipeline    = "data_analytics"
      # Segunda a Sexta: 09:00, 13:00, 22:00 (Horário de Brasília)
      cron        = "0 0 9,13,22 ? * MON-FRI"
      tags = {
        pipeline = "data_analytics"
        type     = "dlt"
        domain   = "data_analytics"
      }
    }
    
    digital_analytics = {
      name        = "dlt-digital-analytics-pipeline"
      description = "Executa pipeline DLT Digital Analytics (Bronze→Silver→Gold)"
      pipeline    = "digital_analytics"
      # Segunda a Sexta: 10:00, 14:00, 23:00 (Horário de Brasília)
      cron        = "0 0 10,14,23 ? * MON-FRI"
      tags = {
        pipeline = "digital_analytics"
        type     = "dlt"
        domain   = "digital_analytics"
      }
    }
  }
}

# ============================================================================
# Resource: Databricks Jobs for DLT Pipelines
# ============================================================================
resource "databricks_job" "dlt_pipeline_jobs" {
  for_each = local.dlt_jobs

  name        = each.value.name
  description = each.value.description

  # Tags para identificação
  tags = each.value.tags

  # Schedule (horários espaçados)
  schedule {
    quartz_cron_expression = each.value.cron
    timezone_id            = "America/Sao_Paulo"
    pause_status           = "UNPAUSED"
  }

  # Task: Executa notebook com parâmetro específico
  task {
    task_key = "run-pipeline"

    notebook_task {
      notebook_path = "/Shared/linkedin_pipeline_runner_notebook"
      source        = "WORKSPACE"
      
      # PARÂMETROS CRÍTICOS:
      # - pipeline: Define qual pipeline DLT executar
      # - environment: production
      base_parameters = {
        pipeline    = each.value.pipeline
        environment = "production"
      }
    }

    # Timeout: 1 hora (3600 segundos)
    timeout_seconds = 3600

    # Retry: 1 tentativa em caso de falha
    max_retries             = 1
    min_retry_interval_millis = 60000
    retry_on_timeout        = false
  }

  # Email notifications (opcional)
  email_notifications {
    no_alert_for_skipped_runs = true
  }
}

# ============================================================================
# Outputs: Job IDs para referência
# ============================================================================
output "dlt_job_ids" {
  description = "IDs dos jobs DLT criados"
  value = {
    for k, v in databricks_job.dlt_pipeline_jobs : k => v.id
  }
}

output "dlt_job_urls" {
  description = "URLs dos jobs DLT no Databricks UI"
  value = {
    for k, v in databricks_job.dlt_pipeline_jobs : k => v.url
  }
}

# ============================================================================
# COMO USAR:
# ============================================================================
# 1. Configurar variáveis de ambiente:
#    export DATABRICKS_HOST="https://dbc-xxxxx.cloud.databricks.com"
#    export DATABRICKS_TOKEN="dapi..."
#
# 2. Inicializar Terraform:
#    cd terraform/
#    terraform init
#
# 3. Planejar mudanças:
#    terraform plan
#
# 4. Aplicar (criar jobs):
#    terraform apply
#
# 5. Ver IDs criados:
#    terraform output dlt_job_ids
#
# ============================================================================
# BENEFÍCIOS:
# ============================================================================
# ✅ Infraestrutura como código (versionada no Git)
# ✅ Jobs criados automaticamente (sem UI manual)
# ✅ Configuração consistente (sem erros humanos)
# ✅ Fácil replicar em outros ambientes
# ✅ Horários parametrizados e documentados
# ✅ Rollback fácil (terraform destroy)
# ============================================================================
