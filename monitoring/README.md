# 🔍 Monitoramento - Vagas LinkedIn

Monitoramento completo do pipeline: GCP (Cloud Run) + Databricks Jobs.

---

## 📊 **Visão Geral**

Este sistema monitora automaticamente:

### **☁️ Google Cloud Platform:**
- ✅ Cloud Run Jobs (staging/production)
- ✅ Execuções e status
- ✅ Logs e erros
- ✅ Dados no Cloud Storage (freshness)

### **🧱 Databricks:**
- ✅ Jobs DLT (Transform Agent)
- ✅ Agent Chat (Telegram notifications)
- ✅ Taxa de sucesso dos runs
- ✅ Alertas de falhas

---

## 🚀 **Como Funciona**

### **1. Monitoramento Automático via GitHub Actions**

**Workflow:** `.github/workflows/monitoring.yml`

**Schedule:** A cada **6 horas**

**O que faz:**
1. Roda smoke tests no Cloud Run
2. Verifica status dos jobs Databricks
3. Envia alertas via Telegram se houver problemas
4. Gera relatório de monitoramento

**Executar manualmente:**
```bash
# Via GitHub Actions UI
# Ou via gh CLI:
gh workflow run monitoring.yml
```

---

### **2. Terraform - Alertas GCP**

**Arquivo:** `terraform/monitoring.tf`

**Recursos criados:**
- 📧 **Notification Channel** (email)
- 🚨 **Alert Policies** (3 alertas)
- 📊 **Dashboard** (métricas Cloud Run)
- ⏰ **Cloud Scheduler** (execução automática 3x/dia)

**Alertas configurados:**

| Alerta | Condição | Ação |
|--------|----------|------|
| **Job Failures** | Run falhou | Email imediato |
| **Slow Execution** | > 10 minutos | Email |
| **No Executions** | Sem runs em 24h | Email |

**Aplicar:**
```bash
cd terraform/
terraform init
terraform apply -var manage_gcp_resources=true
```

---

### **3. Script Python - Monitor Databricks**

**Arquivo:** `monitoring/databricks_monitor.py`

**O que faz:**
- Lista todos os jobs críticos
- Verifica última execução
- Calcula taxa de sucesso (últimos 5 runs)
- Envia alertas Telegram se houver falhas

**Jobs monitorados:**
- `linkedin-agent-chat-notifications`
- `linkedin-dlt-pipeline`
- `linkedin-extract-agent`

**Executar manualmente:**
```bash
# Configurar variáveis
export DATABRICKS_HOST="https://dbc-xxxxx.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi..."
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="123456789"

# Executar
python monitoring/databricks_monitor.py
```

**Saída esperada:**
```
🔍 Monitorando jobs críticos do Databricks...
============================================================
✅ linkedin-agent-chat-notifications
   Status: HEALTHY
   Mensagem: Último run bem-sucedido há 2.3h
   Taxa de Sucesso: 100.0%

⚠️ linkedin-dlt-pipeline
   Status: STALE
   Mensagem: Último run bem-sucedido há 26.5h
   Taxa de Sucesso: 80.0%

============================================================
✅ Monitoramento concluído
📊 Jobs verificados: 3
📨 Alertas enviados: 1
```

---

## 🎯 **Cloud Scheduler - Migração do V5 para Staging**

### **Antes (manual):**
Você tinha um Cloud Scheduler apontando para `vaga-linkedin-prod-v5`.

### **Agora (Terraform):**
O Terraform cria automaticamente um novo scheduler para `vaga-linkedin-prod-staging`.

**Configuração:**
```hcl
# terraform/monitoring.tf
resource "google_cloud_scheduler_job" "cloud_run_job_trigger" {
  name        = "vaga-linkedin-prod-staging-trigger"
  description = "Trigger automático 3x/dia"
  
  # 08:00, 14:00, 20:00 BRT
  schedule    = "0 8,14,20 * * *"
  time_zone   = "America/Sao_Paulo"
  
  http_target {
    uri = "https://us-central1-run.googleapis.com/.../jobs/vaga-linkedin-prod-staging:run"
    ...
  }
}
```

**Aplicar:**
```bash
cd terraform/
terraform apply -var manage_gcp_resources=true
```

**Verificar:**
```bash
gcloud scheduler jobs list --location=us-central1 --project=vaga-linkedin
```

**Deletar scheduler antigo (se quiser):**
```bash
# Listar schedulers existentes
gcloud scheduler jobs list --location=us-central1 --project=vaga-linkedin

# Deletar o antigo (se existir)
gcloud scheduler jobs delete vaga-linkedin-prod-v5-trigger \
  --location=us-central1 \
  --project=vaga-linkedin
```

---

## 📧 **Configuração de Notificações**

### **Email (GCP Monitoring):**

Configurado via Terraform:
```hcl
variable "current_user_email" {
  description = "Email para receber alertas"
  type        = string
}
```

**Aplicar:**
```bash
cd terraform/
terraform apply -var current_user_email="seu-email@gmail.com"
```

### **Telegram (Databricks):**

1. **Criar bot via BotFather**
2. **Obter Chat ID**
3. **Configurar no Databricks Secrets:**

```bash
databricks secrets create-scope vagas_linkedin
databricks secrets put --scope vagas_linkedin --key telegram-bot-token
databricks secrets put --scope vagas_linkedin --key telegram-chat-id
```

4. **Configurar no GitHub Secrets:**

```bash
gh secret set TELEGRAM_BOT_TOKEN
gh secret set TELEGRAM_CHAT_ID
```

---

## 📊 **Dashboard GCP**

**Criado via Terraform:**
- Execuções por status (sucesso/falha)
- Tempo de execução
- Logs recentes

**Acessar:**
```bash
# Via CLI
gcloud monitoring dashboards list --project=vaga-linkedin

# Via Console
https://console.cloud.google.com/monitoring/dashboards?project=vaga-linkedin
```

---

## 🧪 **Smoke Tests**

**Arquivo:** `tests/smoke/test_cloud_run_smoke.py`

**O que testa:**
- ✅ Job existe no Cloud Run
- ✅ Imagem está correta
- ✅ Recursos (CPU/RAM) configurados
- ✅ Secret RAPIDAPI_KEY presente
- ✅ Execuções recentes
- ✅ Dados no Cloud Storage
- ✅ Logs sendo gerados

**Executar localmente:**
```bash
# Instalar dependências
pip install pytest google-cloud-run google-cloud-logging google-cloud-storage

# Configurar variáveis
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/gcp-credentials.json"
export GCP_PROJECT_ID="vaga-linkedin"
export GCP_REGION="us-central1"
export ENVIRONMENT="staging"

# Rodar testes
pytest tests/smoke/ -v
```

**No CI/CD:**
Roda automaticamente após cada deploy (`.github/workflows/ci-cd-pipeline.yml`).

---

## 🔧 **Troubleshooting**

### **Problema: Alertas não estão sendo enviados**

**Verificar:**
1. Notification channel configurado?
```bash
gcloud alpha monitoring channels list --project=vaga-linkedin
```

2. Email confirmado?
- Check inbox/spam
- Google Cloud Console → Monitoring → Notification Channels

3. Alert policies habilitadas?
```bash
gcloud alpha monitoring policies list --project=vaga-linkedin
```

### **Problema: Databricks monitor falha**

**Verificar:**
1. Token válido?
```bash
curl -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  "$DATABRICKS_HOST/api/2.0/clusters/list"
```

2. Jobs existem?
```bash
python monitoring/databricks_monitor.py
```

3. Telegram configurado?
```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"
```

### **Problema: Cloud Scheduler não está rodando**

**Verificar:**
1. Scheduler criado?
```bash
gcloud scheduler jobs list --location=us-central1 --project=vaga-linkedin
```

2. Service account tem permissões?
```bash
gcloud projects get-iam-policy vaga-linkedin \
  --flatten="bindings[].members" \
  --filter="bindings.members:linkedin-scraper@vaga-linkedin.iam.gserviceaccount.com"
```

3. Forçar execução manual:
```bash
gcloud scheduler jobs run vaga-linkedin-prod-staging-trigger \
  --location=us-central1 \
  --project=vaga-linkedin
```

---

## 📚 **Referências**

- [Cloud Monitoring Docs](https://cloud.google.com/monitoring/docs)
- [Cloud Scheduler Docs](https://cloud.google.com/scheduler/docs)
- [Databricks Jobs API](https://docs.databricks.com/api/workspace/jobs)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

## ✅ **Checklist de Implementação**

- [ ] ✅ Smoke tests criados
- [ ] ✅ Monitoring Terraform aplicado
- [ ] ✅ Cloud Scheduler configurado (3x/dia)
- [ ] ✅ Email alerts configurados
- [ ] ✅ Telegram bot configurado
- [ ] ✅ Databricks monitor testado
- [ ] ✅ GitHub Actions workflow ativo
- [ ] ✅ Dashboard GCP acessível
- [ ] ✅ Scheduler antigo (v5) deletado

---

**Última atualização:** 08/10/2025  
**Versão:** 1.0  
**Status:** ✅ Pronto para uso
