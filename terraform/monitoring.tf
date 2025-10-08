# ==================== CLOUD MONITORING & ALERTING ====================
# Configuração de monitoramento para Cloud Run Jobs e alertas

# Notification Channel - Email
resource "google_monitoring_notification_channel" "email" {
  count        = var.manage_gcp_resources ? 1 : 0
  project      = var.gcp_project_id
  display_name = "Email Notifications - Vagas LinkedIn"
  type         = "email"

  labels = {
    email_address = var.current_user_email
  }

  enabled = true
}

# Alert Policy - Cloud Run Job Failures
resource "google_monitoring_alert_policy" "cloud_run_job_failure" {
  count        = var.manage_gcp_resources ? 1 : 0
  project      = var.gcp_project_id
  display_name = "Cloud Run Job - Falhas de Execução"

  documentation {
    content   = "Cloud Run Job ${var.cloud_run_job_name} falhou na execução. Verifique os logs em Cloud Logging."
    mime_type = "text/markdown"
  }

  conditions {
    display_name = "Job Execution Failed"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_job\" AND resource.labels.job_name = \"${var.cloud_run_job_name}\" AND metric.type = \"run.googleapis.com/job/completed_execution_count\" AND metric.labels.result = \"failed\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  combiner = "OR"

  notification_channels = [google_monitoring_notification_channel.email[0].name]

  alert_strategy {
    auto_close = "604800s" # 7 dias
  }

  enabled = true
}

# Alert Policy - Cloud Run Job Execution Time
resource "google_monitoring_alert_policy" "cloud_run_job_slow" {
  count        = var.manage_gcp_resources ? 1 : 0
  project      = var.gcp_project_id
  display_name = "Cloud Run Job - Execução Lenta"

  documentation {
    content   = "Cloud Run Job ${var.cloud_run_job_name} está demorando mais que 10 minutos. Pode haver problema na extração."
    mime_type = "text/markdown"
  }

  conditions {
    display_name = "Job Execution Duration > 10min"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_job\" AND resource.labels.job_name = \"${var.cloud_run_job_name}\" AND metric.type = \"run.googleapis.com/job/execution/duration\""
      duration        = "120s"
      comparison      = "COMPARISON_GT"
      threshold_value = 600 # 10 minutos em segundos

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  combiner = "OR"

  notification_channels = [google_monitoring_notification_channel.email[0].name]

  alert_strategy {
    auto_close = "86400s" # 1 dia
  }

  enabled = true
}

# Alert Policy - No Recent Executions (Job não rodou nas últimas 24h)
resource "google_monitoring_alert_policy" "cloud_run_job_not_running" {
  count        = var.manage_gcp_resources ? 1 : 0
  project      = var.gcp_project_id
  display_name = "Cloud Run Job - Sem Execuções Recentes"

  documentation {
    content   = "Cloud Run Job ${var.cloud_run_job_name} não teve execuções nas últimas 24 horas. Verifique o Cloud Scheduler."
    mime_type = "text/markdown"
  }

  conditions {
    display_name = "No Executions in 24h"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_job\" AND resource.labels.job_name = \"${var.cloud_run_job_name}\" AND metric.type = \"run.googleapis.com/job/completed_execution_count\""
      duration        = "86400s" # 24 horas
      comparison      = "COMPARISON_LT"
      threshold_value = 1

      aggregations {
        alignment_period   = "3600s" # 1 hora
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  combiner = "OR"

  notification_channels = [google_monitoring_notification_channel.email[0].name]

  alert_strategy {
    auto_close = "172800s" # 2 dias
  }

  enabled = true
}

# Dashboard - Cloud Run Job Monitoring
resource "google_monitoring_dashboard" "cloud_run_job" {
  count   = var.manage_gcp_resources ? 1 : 0
  project = var.gcp_project_id
  dashboard_json = jsonencode({
    displayName = "Cloud Run Job - Vagas LinkedIn"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Execuções por Status"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type = \"cloud_run_job\" AND resource.labels.job_name = \"${var.cloud_run_job_name}\" AND metric.type = \"run.googleapis.com/job/completed_execution_count\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_RATE"
                        crossSeriesReducer = "REDUCE_SUM"
                        groupByFields      = ["metric.label.result"]
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
            }
          }
        },
        {
          xPos   = 6
          width  = 6
          height = 4
          widget = {
            title = "Tempo de Execução"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type = \"cloud_run_job\" AND resource.labels.job_name = \"${var.cloud_run_job_name}\" AND metric.type = \"run.googleapis.com/job/execution/duration\""
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
            }
          }
        },
        {
          yPos   = 4
          width  = 12
          height = 4
          widget = {
            title = "Logs Recentes"
            logsPanel = {
              resourceNames = ["projects/${var.gcp_project_id}"]
              filter        = "resource.type=\"cloud_run_job\" resource.labels.job_name=\"${var.cloud_run_job_name}\""
            }
          }
        }
      ]
    }
  })
}

# ==================== CLOUD SCHEDULER ====================
# Agendamento automático do Cloud Run Job

resource "google_cloud_scheduler_job" "cloud_run_job_trigger" {
  count       = var.manage_gcp_resources ? 1 : 0
  project     = var.gcp_project_id
  region      = var.gcp_region
  name        = "${var.cloud_run_job_name}-trigger"
  description = "Trigger automático para ${var.cloud_run_job_name}"

  # Schedule: 3x por dia (08:00, 14:00, 20:00 BRT = 11:00, 17:00, 23:00 UTC)
  schedule  = var.cloud_scheduler_cron
  time_zone = "America/Sao_Paulo"

  http_target {
    uri         = "https://${var.gcp_region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.gcp_project_id}/jobs/${var.cloud_run_job_name}:run"
    http_method = "POST"

    oauth_token {
      service_account_email = var.gcp_service_account_email
    }
  }

  retry_config {
    retry_count          = 3
    max_retry_duration   = "600s"
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
  }
}

# ==================== UPTIME CHECKS (OPCIONAL) ====================
# Verifica se o job rodou recentemente checando dados no GCS

resource "google_monitoring_uptime_check_config" "gcs_data_check" {
  count        = var.manage_gcp_resources && var.enable_uptime_checks ? 1 : 0
  project      = var.gcp_project_id
  display_name = "GCS Data Freshness - Bronze Raw"
  timeout      = "10s"
  period       = "3600s" # Verifica a cada 1 hora

  http_check {
    path           = "/linkedin-dados-raw/bronze-raw/"
    port           = 443
    use_ssl        = true
    validate_ssl   = true
    request_method = "GET"
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.gcp_project_id
      host       = "storage.googleapis.com"
    }
  }
}
