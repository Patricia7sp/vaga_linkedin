# 🏗️ Arquitetura CI/CD - Vagas LinkedIn

## 📊 **Visão Geral**

Este projeto utiliza uma arquitetura **híbrida** com processamento distribuído entre **Google Cloud Platform (GCP)** e **Databricks**.

---

## 🔄 **Fluxo Completo da Arquitetura**

```
┌──────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS (CI/CD)                     │
│  Push → Build → Test → Deploy (GCP) → Trigger (Databricks)  │
└──────────────────┬───────────────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │   GOOGLE CLOUD      │
        │   (Extract)         │
        │                     │
        │ ┌─────────────────┐ │
        │ │  Cloud Run Job  │ │
        │ │  (Staging/Prod) │ │
        │ │                 │ │
        │ │ Extract Agent   │ │
        │ │   ↓             │ │
        │ │ RapidAPI        │ │
        │ │   ↓             │ │
        │ │ LinkedIn Data   │ │
        │ └────────┬────────┘ │
        └──────────┼──────────┘
                   │
        ┌──────────▼──────────┐
        │  Cloud Storage      │
        │  (bronze-raw)       │
        │  JSONL/Parquet      │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────────────────────┐
        │        DATABRICKS                   │
        │   (Transform + Analytics)           │
        │                                     │
        │ ┌─────────────────────────────────┐ │
        │ │  Load Agent                     │ │
        │ │  GCS → Unity Catalog (bronze)   │ │
        │ └─────────────┬───────────────────┘ │
        │               │                     │
        │ ┌─────────────▼───────────────────┐ │
        │ │  Transform Agent (DLT)          │ │
        │ │  Bronze → Silver → Gold         │ │
        │ └─────────────┬───────────────────┘ │
        │               │                     │
        │ ┌─────────────▼───────────────────┐ │
        │ │  Viz Agent                      │ │
        │ │  Dashboards + Lakeview          │ │
        │ └─────────────┬───────────────────┘ │
        │               │                     │
        │ ┌─────────────▼───────────────────┐ │
        │ │  Agent Chat                     │ │
        │ │  Telegram Notifications         │ │
        │ └─────────────────────────────────┘ │
        └─────────────────────────────────────┘
```

---

## 🎯 **Divisão de Responsabilidades**

### **☁️ Google Cloud Platform (GCP)**

#### **Cloud Run Jobs**

| Job | Trigger | Função | Recursos |
|-----|---------|--------|----------|
| `vaga-linkedin-prod-staging` | CI/CD (branch main) | **Extract Agent** - Extração LinkedIn | 2Gi RAM, 1 CPU |
| `vaga-linkedin-prod-v5` | Manual ou CI/CD | **Extract Agent** - Produção | 4Gi RAM, 2 CPU |

**Responsabilidades:**
- ✅ Extração de dados do LinkedIn via RapidAPI
- ✅ Salvamento em Cloud Storage (bronze-raw)
- ✅ Envio para Kafka (opcional)
- ✅ Logs e monitoramento

**Secrets Necessários:**
- `RAPIDAPI_KEY` → API LinkedIn Job Search

---

### **🧱 Databricks**

#### **Jobs Databricks**

**Responsabilidades:**
1. **Load Agent** - Carregar dados do GCS para Unity Catalog (bronze)
2. **Transform Agent** - DLT Pipelines (Bronze → Silver → Gold)
3. **Viz Agent** - Criar views e dashboards Lakeview
4. **Agent Chat** - Notificações Telegram (a cada 4h)

**Secrets Necessários:**
- `DATABRICKS_TOKEN` → Autenticação Databricks
- `TELEGRAM_BOT_TOKEN` → Notificações Telegram
- `TELEGRAM_CHAT_ID` → ID do chat Telegram

---

## 🔐 **Gestão de Secrets**

### **GitHub Secrets** (para CI/CD)

Usados durante build e deploy no GitHub Actions:

```yaml
DATABRICKS_HOST: https://dbc-xxxxx.cloud.databricks.com
DATABRICKS_TOKEN: dapi...
GCP_SERVICE_ACCOUNT_KEY: {...json...}
RAPIDAPI_KEY: xxxxx
TELEGRAM_BOT_TOKEN: xxxxx
```

### **GCP Secret Manager** (para Cloud Run)

Usados em runtime pelo Cloud Run Job:

```bash
rapidapi-key:latest        # ✅ Único secret necessário
```

### **Databricks Secrets** (para Databricks Jobs)

Configurados via Databricks CLI ou UI:

```bash
databricks secrets create-scope vagas_linkedin
databricks secrets put --scope vagas_linkedin --key databricks-token
databricks secrets put --scope vagas_linkedin --key telegram-bot-token
databricks secrets put --scope vagas_linkedin --key telegram-chat-id
```

---

## 🚀 **Cloud Run Jobs - Detalhes**

### **Diferença entre os Jobs**

| Aspecto | `vaga-linkedin-prod-v5` (OLD) | `vaga-linkedin-prod-staging` (NEW) |
|---------|-------------------------------|-------------------------------------|
| **Criação** | Manual | **Automático via CI/CD** ✅ |
| **Trigger** | Manual | **Push na branch main** ✅ |
| **Imagem** | Fixa (v5) | **Atualizada a cada commit** ✅ |
| **Uso** | Produção legada | **Staging/Validação** ✅ |
| **Status** | Pode ser desativado | **Ativo e recomendado** ✅ |

### **Recomendação: Use `vaga-linkedin-prod-staging`**

O job **staging** é gerenciado automaticamente pelo CI/CD:
- ✅ Sempre com a versão mais recente do código
- ✅ Deploy automático a cada push
- ✅ Testado antes de ir para produção
- ✅ Logs integrados com GitHub Actions

O job **v5** pode ser:
- 🔄 Mantido para deploys manuais críticos
- ⏸️ Desativado se não for mais usado
- 🔁 Renomeado para `vaga-linkedin-prod-production` se quiser manter a nomenclatura

---

## 📝 **Workflow CI/CD**

### **Branches e Ambientes**

```yaml
develop → deploy-dev       # (opcional) Ambiente de testes
main    → deploy-staging   # ✅ Deploy automático (RECOMENDADO)
tag v*  → deploy-prod      # (opcional) Deploy manual para produção
```

### **Stages do Pipeline**

1. **🔍 Code Quality & Linting** (2min)
   - Black, isort, Flake8, Pylint, MyPy
   - Bandit (segurança)
   - Safety (dependências)

2. **🧪 Unit Tests** (2min)
   - Pytest com coverage
   - Mínimo 70% coverage (warning only)

3. **🏗️ Terraform Validation** (15s)
   - terraform fmt, validate
   - TFLint

4. **🔗 Integration Tests** (2min)
   - Testes de integração
   - Database PostgreSQL

5. **🐳 Docker Build & Scan** (30s)
   - Build da imagem
   - Trivy security scan

6. **🎭 Deploy to Staging** (6-8min)
   - ✅ Autenticação GCP
   - ✅ Build Docker image (Cloud Build)
   - ✅ Deploy Cloud Run Job
   - ⚠️ Smoke Tests (opcional)

7. **🏭 Deploy to Production** (manual)
   - Apenas com workflow_dispatch
   - Cria GitHub Release

---

## 🎯 **Como Executar o Pipeline**

### **1. Deploy Automático (Staging)**

```bash
# Qualquer push na branch main aciona o deploy
git checkout main
git add .
git commit -m "feat: nova funcionalidade"
git push origin main

# GitHub Actions fará automaticamente:
# 1. Testes
# 2. Build Docker
# 3. Deploy no Cloud Run (staging)
```

### **2. Executar Cloud Run Job Manualmente**

```bash
# Via gcloud CLI
gcloud run jobs execute vaga-linkedin-prod-staging \
  --region=us-central1 \
  --project=vaga-linkedin

# Via Console GCP
# https://console.cloud.google.com/run/jobs
# → Selecionar job → EXECUTE
```

### **3. Verificar Logs**

```bash
# Logs do GitHub Actions
gh run list
gh run view <run-id> --log

# Logs do Cloud Run
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=vaga-linkedin-prod-staging" \
  --limit=50 \
  --format=json \
  --project=vaga-linkedin
```

---

## 🔍 **Monitoramento e Observabilidade**

### **Métricas Importantes**

| Métrica | Onde Ver | Objetivo |
|---------|----------|----------|
| **Extract Agent - Sucesso** | Cloud Run Logs | > 95% |
| **Tempo de Extração** | Cloud Run Metrics | < 5min |
| **Jobs Extraídas** | GCS / Databricks | > 100/dia |
| **Pipeline DLT - Sucesso** | Databricks | > 98% |
| **Telegram Notifications** | Telegram | Diário |

### **Dashboards**

1. **GitHub Actions**
   - https://github.com/Patricia7sp/vaga_linkedin/actions

2. **Cloud Run (GCP)**
   - https://console.cloud.google.com/run/jobs?project=vaga-linkedin

3. **Databricks**
   - Workflow Jobs: Jobs → linkedin-agent-chat-notifications
   - DLT Pipelines: Delta Live Tables

---

## 🛠️ **Troubleshooting**

### **Problema: Deploy falha no Cloud Run**

**Erro:** `Secret not found`

**Solução:**
```bash
# Verificar secrets
gcloud secrets list --project=vaga-linkedin

# Criar secret se necessário
echo "SUA_RAPIDAPI_KEY" | gcloud secrets create rapidapi-key \
  --data-file=- \
  --project=vaga-linkedin

# Atualizar job
gcloud run jobs update vaga-linkedin-prod-staging \
  --set-secrets="RAPIDAPI_KEY=rapidapi-key:latest" \
  --region=us-central1 \
  --project=vaga-linkedin
```

### **Problema: Job não executa**

**Solução:**
1. Verificar permissões IAM da service account
2. Verificar logs do Cloud Run
3. Testar localmente com Docker:

```bash
cd app_production
docker build -t vaga-linkedin-test .
docker run --env-file .env vaga-linkedin-test
```

---

## 📚 **Documentação Adicional**

- [Deploy Permissions](../terraform/DEPLOY_PERMISSIONS.md) - Configuração IAM
- [Terraform Setup](../terraform/README.md) - Infraestrutura as Code
- [Extract Agent](../app_production/agents/extract_agent/README.md) - Detalhes extração

---

## ✅ **Checklist de Deploy**

Antes de fazer deploy em produção:

- [ ] ✅ Todos os testes passando (CI/CD green)
- [ ] ✅ Deploy staging executado com sucesso
- [ ] ✅ Secrets configurados no GCP Secret Manager
- [ ] ✅ Permissões IAM configuradas
- [ ] ✅ Cloud Run Job testado manualmente
- [ ] ✅ Databricks pipelines validados
- [ ] ✅ Notificações Telegram funcionando

---

**Última atualização:** 08/10/2025  
**Versão:** 1.0  
**Autor:** AI Assistant + Patricia
