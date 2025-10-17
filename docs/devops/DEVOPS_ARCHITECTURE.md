# 🏗️ DevOps Architecture - GCP + Databricks

## 📋 Visão Geral

Este projeto utiliza uma arquitetura **híbrida** com componentes rodando em **GCP (Cloud Run)** e **Databricks**, com CI/CD unificado gerenciando ambos os ambientes.

---

## 🎯 Arquitetura de Deploy

```
┌─────────────────────────────────────────────────────────────────┐
│                    GITHUB REPOSITORY                             │
│                  (Código fonte único)                            │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                  GITHUB ACTIONS (CI/CD)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐    ┌──────────────────────┐           │
│  │  GCP Pipeline       │    │  Databricks Pipeline │           │
│  │  (Cloud Run)        │    │  (Notebooks + Jobs)  │           │
│  └─────────────────────┘    └──────────────────────┘           │
│           │                            │                         │
└───────────┼────────────────────────────┼─────────────────────────┘
            │                            │
            ▼                            ▼
┌─────────────────────┐    ┌──────────────────────┐
│   GOOGLE CLOUD      │    │    DATABRICKS        │
│                     │    │                      │
│  ┌───────────────┐ │    │  ┌────────────────┐ │
│  │  Cloud Run    │ │    │  │  Notebooks     │ │
│  │  - Extract    │ │    │  │  - Transform   │ │
│  │  - Load       │ │    │  │  - Agent Chat  │ │
│  └───────────────┘ │    │  └────────────────┘ │
│                     │    │                      │
│  ┌───────────────┐ │    │  ┌────────────────┐ │
│  │  GCS Buckets  │ │    │  │  DLT Pipelines │ │
│  │  - Raw Data   │ │    │  │  - Bronze      │ │
│  └───────────────┘ │    │  │  - Silver      │ │
│                     │    │  │  - Gold        │ │
│  ┌───────────────┐ │    │  └────────────────┘ │
│  │  Secret Mgr   │ │    │                      │
│  └───────────────┘ │    │  ┌────────────────┐ │
└─────────────────────┘    │  │  Unity Catalog │ │
                            │  └────────────────┘ │
                            └──────────────────────┘
```

---

## 🔄 Workflows CI/CD

### **1. ci-cd-pipeline.yml** (GCP - Cloud Run)
**Trigger:** Push/PR em `main` ou `develop`  
**Responsável por:**
- ✅ Extração de dados (Extract Agent)
- ✅ Carregamento no GCS (Load Agent)
- ✅ Deploy do Cloud Run Job

**Stages:**
1. Code Quality (Black, Flake8, Pylint)
2. Unit Tests
3. Integration Tests
4. Terraform Validation
5. Docker Build & Scan
6. Deploy DEV
7. Deploy STAGING
8. Deploy PRODUCTION (manual)
9. Post-Deploy Validation

### **2. databricks-deploy.yml** (Databricks)
**Trigger:** Push em arquivos Databricks (`agents/`, `agent_chat.py`, `notebooks/`)  
**Responsável por:**
- ✅ Transformação de dados (Transform Agent)
- ✅ Agent Chat (notificações Telegram)
- ✅ DLT Pipelines (Bronze → Silver → Gold)

**Stages:**
1. Validate Databricks Code
2. Deploy to Databricks DEV
3. Deploy to Databricks STAGING
4. Deploy to Databricks PRODUCTION

### **3. auto-promote-to-prod.yml** (Auto-Promotion)
**Trigger:** Após sucesso do CI/CD Pipeline  
**Responsável por:**
- 🤖 Avaliar critérios de auto-promoção
- ✅ Deploy automático se critérios atendidos
- ⚠️ Solicitar aprovação manual se não atendidos

**Critérios de Auto-Aprovação:**
1. ✅ Horário comercial (seg-sex, 8h-18h)
2. ✅ Não é sexta-feira tarde
3. ✅ Mínimo 30 min em staging
4. ✅ Sem issues críticas abertas
5. ✅ Todos os testes passaram
6. ✅ Code coverage >= 70%
7. ✅ Sem vulnerabilidades críticas

---

## 📁 Estrutura de Arquivos por Ambiente

### **GCP (Cloud Run)**
```
app_production/
├── agents/
│   ├── extract_agent/
│   │   ├── extract_agent.py
│   │   ├── extract_agent_hybrid.py
│   │   └── rapidapi_linkedin_extractor.py
│   └── load_agent/
│       └── load_agent.py
├── Dockerfile
└── requirements.txt
```

### **Databricks**
```
/Shared/
├── agent_chat.py                    # Agent Chat (notificações)
├── notebooks/
│   ├── bronze_pipeline.py
│   ├── silver_pipeline.py
│   └── gold_pipeline.py
└── [env]/                           # dev, staging, prod
    ├── agent_chat.py
    └── notebooks/
```

---

## 🔐 Secrets Management

### **GitHub Secrets (GCP)**
```
GCP_SA_KEY                  # Service Account para Cloud Run
GCP_PROJECT_ID              # vaga-linkedin
```

### **GitHub Secrets (Databricks)**
```
DATABRICKS_HOST             # https://dbc-14d16b60-2882.cloud.databricks.com
DATABRICKS_TOKEN            # Token de acesso
DATABRICKS_HOST_DEV         # Workspace DEV (opcional)
DATABRICKS_TOKEN_DEV        # Token DEV (opcional)
```

### **GitHub Secrets (Compartilhados)**
```
RAPIDAPI_KEY                # RapidAPI
TELEGRAM_BOT_TOKEN          # Telegram
TELEGRAM_CHAT_ID            # Telegram
SLACK_WEBHOOK               # Notificações
```

---

## 🚀 Fluxo de Deploy Completo

### **Cenário 1: Deploy Automático (Critérios Atendidos)**
```
1. Developer: git push origin main
2. GitHub Actions: Executa ci-cd-pipeline.yml
   ├─ Code Quality ✅
   ├─ Tests ✅
   ├─ Build Docker ✅
   ├─ Deploy GCP DEV ✅
   └─ Deploy GCP STAGING ✅
3. GitHub Actions: Executa databricks-deploy.yml
   ├─ Validate Code ✅
   ├─ Deploy Databricks DEV ✅
   └─ Deploy Databricks STAGING ✅
4. GitHub Actions: Executa auto-promote-to-prod.yml
   ├─ Evaluate Criteria ✅
   ├─ Auto-Deploy GCP PROD ✅
   ├─ Auto-Deploy Databricks PROD ✅
   └─ Create Release ✅
5. Slack: Notificação de sucesso 🎉
```

### **Cenário 2: Deploy Manual (Critérios NÃO Atendidos)**
```
1. Developer: git push origin main
2. GitHub Actions: Executa ci-cd-pipeline.yml
   ├─ Code Quality ✅
   ├─ Tests ✅
   ├─ Build Docker ✅
   ├─ Deploy GCP DEV ✅
   └─ Deploy GCP STAGING ✅
3. GitHub Actions: Executa databricks-deploy.yml
   ├─ Validate Code ✅
   ├─ Deploy Databricks DEV ✅
   └─ Deploy Databricks STAGING ✅
4. GitHub Actions: Executa auto-promote-to-prod.yml
   ├─ Evaluate Criteria ❌ (ex: fora do horário)
   └─ Comment: "Manual approval required"
5. Developer: Acessa GitHub Actions
6. Developer: Executa workflow manualmente
7. Approver: Aprova deploy
8. GitHub Actions: Deploy PROD ✅
```

---

## 📊 Ambientes

| Ambiente | GCP Cloud Run | Databricks Workspace | Deploy |
|----------|---------------|---------------------|--------|
| **DEV** | `vaga-linkedin-prod-dev` | `/Shared/dev/` | Automático |
| **STAGING** | `vaga-linkedin-prod-staging` | `/Shared/staging/` | Automático |
| **PROD** | `vaga-linkedin-prod-v5` | `/Shared/` | Auto ou Manual |

---

## 🎯 Vantagens da Arquitetura

### **1. Unificação**
- ✅ Um único repositório
- ✅ Um único pipeline CI/CD
- ✅ Gestão centralizada

### **2. Separação de Responsabilidades**
- ✅ GCP: Extração e carregamento (rápido, escalável)
- ✅ Databricks: Transformação e análise (Spark, DLT)

### **3. Deploy Inteligente**
- ✅ Auto-promoção baseada em critérios
- ✅ Rollback automático
- ✅ Validação em múltiplas camadas

### **4. Segurança**
- ✅ Secrets segregados por ambiente
- ✅ Aprovação manual quando necessário
- ✅ Scanning de vulnerabilidades

---

## 🔧 Comandos Úteis

### **Ver status do deploy GCP:**
```bash
gcloud run jobs describe vaga-linkedin-prod-v5 \
  --region=us-central1 --project=vaga-linkedin
```

### **Ver status do deploy Databricks:**
```bash
databricks workspace ls /Shared/
```

### **Forçar deploy manual:**
```bash
# Via GitHub Actions UI
# Ou via gh CLI:
gh workflow run ci-cd-pipeline.yml -f environment=prod
```

---

## 📚 Próximos Passos

1. ✅ Configurar secrets no GitHub
2. ✅ Testar deploy em DEV
3. ✅ Validar auto-promoção
4. ✅ Ajustar critérios conforme necessário
5. ✅ Monitorar métricas de deploy

---

**Última atualização:** 2025-10-06  
**Versão:** 2.0 (Arquitetura Híbrida)
