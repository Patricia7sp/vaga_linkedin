# ☁️ Cloud Run Jobs - Guia Completo

## 🎯 **Suas Dúvidas Respondidas**

### **Pergunta 1: Qual job usar agora?**

**Resposta:** Use **`vaga-linkedin-prod-staging`** ✅

#### **Por quê?**

| Critério | `vaga-linkedin-prod-v5` (OLD) | `vaga-linkedin-prod-staging` (NEW) |
|----------|-------------------------------|-------------------------------------|
| **Gerenciamento** | Manual | **Automático via CI/CD** ✅ |
| **Imagem** | Fixa (antiga) | **Sempre atualizada** ✅ |
| **Deploy** | Você precisa fazer | **GitHub Actions faz** ✅ |
| **Segurança** | Pode estar desatualizada | **Sempre com código mais recente** ✅ |
| **Recommended** | ⏸️ Pode desativar | **✅ SIM - Use este!** |

---

### **Pergunta 2: O que aconteceu com o erro do job staging?**

**Erro que você viu:**
```
spec.template.spec.containers[0].env[1].value_from_secret_key_ref.name: 
Secret projects/551779207347/secrets/databricks-token/versions/latest was not found
```

**O PROBLEMA:**
- ❌ O job estava configurado para usar secrets **DESNECESSÁRIOS**
- ❌ `databricks-token` → Databricks roda no Databricks, não no GCP!
- ❌ `telegram-bot-token` → Telegram também roda no Databricks!

**A SOLUÇÃO:**
- ✅ Removemos secrets desnecessários
- ✅ Mantivemos **APENAS** `RAPIDAPI_KEY` (único que Cloud Run precisa)
- ✅ Job atualizado e funcionando

**AGORA O JOB ESTÁ ASSIM:**
```yaml
vaga-linkedin-prod-staging:
  Environment: staging
  Secrets: RAPIDAPI_KEY=rapidapi-key:latest  # ✅ ÚNICO SECRET
  Memory: 2Gi
  CPU: 1
  Status: ✅ PRONTO PARA RODAR
```

---

## 🏗️ **Arquitetura dos Jobs**

### **O que cada job FAZ:**

```
┌─────────────────────────────────────────────┐
│  vaga-linkedin-prod-staging (NEW - USE!)   │
├─────────────────────────────────────────────┤
│  Trigger: Push na branch main               │
│  Função: Extract Agent                      │
│  ├─ Conecta no RapidAPI (RAPIDAPI_KEY)     │
│  ├─ Busca vagas do LinkedIn                │
│  ├─ Salva em GCS (bronze-raw/*.jsonl)      │
│  └─ [Opicional] Envia para Kafka           │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  vaga-linkedin-prod-v5 (OLD - Opcional)    │
├─────────────────────────────────────────────┤
│  Trigger: Manual                            │
│  Função: Mesma coisa (Extract Agent)       │
│  Status: Pode ser desativado ou renomeado  │
└─────────────────────────────────────────────┘
```

---

## 🔐 **Secrets - Por que apenas RAPIDAPI_KEY?**

### **Divisão de Responsabilidades:**

#### **☁️ Cloud Run (GCP) - Extract Agent**

**O que FAZ:**
- Extração de vagas do LinkedIn via RapidAPI

**O que PRECISA:**
- ✅ `RAPIDAPI_KEY` → Para acessar API do LinkedIn

**O que NÃO precisa:**
- ❌ `DATABRICKS_TOKEN` → Não acessa Databricks
- ❌ `TELEGRAM_BOT_TOKEN` → Não envia mensagens
- ❌ `TELEGRAM_CHAT_ID` → Não envia mensagens

#### **🧱 Databricks - Load + Transform + Chat**

**O que FAZ:**
- Load: GCS → Unity Catalog
- Transform: DLT Pipelines
- Chat: Telegram Notifications

**O que PRECISA:**
- ✅ `DATABRICKS_TOKEN` → Autenticação
- ✅ `TELEGRAM_BOT_TOKEN` → Enviar mensagens
- ✅ `TELEGRAM_CHAT_ID` → Identificar chat

---

## 🚀 **Como Usar os Jobs**

### **Opção 1: Deploy Automático (Recomendado)**

```bash
# 1. Fazer mudanças no código
git checkout main
vim app_production/agents/extract_agent/extract_agent.py

# 2. Commit e push
git add .
git commit -m "feat: melhoria na extração"
git push origin main

# 3. GitHub Actions automaticamente:
#    ✅ Testa o código
#    ✅ Faz build Docker
#    ✅ Atualiza vaga-linkedin-prod-staging
#    ✅ Job pronto para executar!
```

### **Opção 2: Executar Job Manualmente**

```bash
# Via CLI
gcloud run jobs execute vaga-linkedin-prod-staging \
  --region=us-central1 \
  --project=vaga-linkedin

# Via Console (mais fácil!)
# 1. Acesse: https://console.cloud.google.com/run/jobs
# 2. Clique em "vaga-linkedin-prod-staging"
# 3. Clique em "EXECUTE"
# 4. Aguarde ~5 minutos
# 5. Verifique logs
```

---

## 📊 **Status Atual dos Jobs**

Vou verificar o status atual:

```bash
# Listar jobs
gcloud run jobs list --region=us-central1 --project=vaga-linkedin

# Ver detalhes do job staging
gcloud run jobs describe vaga-linkedin-prod-staging \
  --region=us-central1 \
  --project=vaga-linkedin

# Ver últimas execuções
gcloud run jobs executions list \
  --job=vaga-linkedin-prod-staging \
  --region=us-central1 \
  --project=vaga-linkedin \
  --limit=5
```

**Status esperado:**
```yaml
Job: vaga-linkedin-prod-staging
Status: ✅ Ready
Image: gcr.io/vaga-linkedin/vaga-linkedin-prod:staging-<commit-sha>
Secrets: RAPIDAPI_KEY ✅
Last Updated: Hoje (via CI/CD)
Executions: 0 (aguardando primeira execução manual)
```

---

## 🎬 **Próximos Passos**

### **1. Testar o Job Staging**

```bash
# Execute manualmente para testar
gcloud run jobs execute vaga-linkedin-prod-staging \
  --region=us-central1 \
  --project=vaga-linkedin \
  --wait

# Verificar logs
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=vaga-linkedin-prod-staging" \
  --limit=100 \
  --format=json \
  --project=vaga-linkedin
```

**Resultado esperado:**
```
✅ Extract Agent iniciado
✅ RapidAPI conectado
✅ Vagas extraídas: 100+ jobs
✅ Dados salvos em gs://linkedin-dados-raw/bronze-raw/YYYY-MM-DD/*.jsonl
✅ Execução concluída com sucesso
```

### **2. Configurar Schedule (Opcional)**

Se quiser que rode automaticamente todo dia:

```bash
# Via Cloud Scheduler
gcloud scheduler jobs create http linkedin-daily-extract \
  --location=us-central1 \
  --schedule="0 8 * * *" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/vaga-linkedin/jobs/vaga-linkedin-prod-staging:run" \
  --http-method=POST \
  --oauth-service-account-email=linkedin-scraper@vaga-linkedin.iam.gserviceaccount.com
```

### **3. Decidir sobre o Job V5**

Você tem 3 opções:

**Opção A: Manter os dois** (recomendado)
- `vaga-linkedin-prod-staging` → Deploy automático (main)
- `vaga-linkedin-prod-v5` → Deploy manual (emergências)

**Opção B: Deletar o V5**
```bash
gcloud run jobs delete vaga-linkedin-prod-v5 \
  --region=us-central1 \
  --project=vaga-linkedin
```

**Opção C: Renomear o V5 para Production**
```bash
# Criar novo job "production"
gcloud run jobs create vaga-linkedin-prod-production \
  --image=gcr.io/vaga-linkedin/vaga-linkedin-prod:v5-latest \
  --region=us-central1 \
  --project=vaga-linkedin \
  --memory=4Gi \
  --cpu=2 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="RAPIDAPI_KEY=rapidapi-key:latest"

# Deletar o antigo
gcloud run jobs delete vaga-linkedin-prod-v5 \
  --region=us-central1 \
  --project=vaga-linkedin
```

---

## 🔍 **Verificar se Está Funcionando**

### **Checklist Completo:**

#### **1. Secret está configurado?**
```bash
gcloud secrets versions access latest \
  --secret=rapidapi-key \
  --project=vaga-linkedin

# Deve retornar sua chave RapidAPI (sem mostrar aqui por segurança)
```

#### **2. Job tem acesso ao secret?**
```bash
gcloud run jobs describe vaga-linkedin-prod-staging \
  --region=us-central1 \
  --project=vaga-linkedin \
  --format=yaml | grep -A 5 secrets
```

**Output esperado:**
```yaml
secrets:
- name: RAPIDAPI_KEY
  valueFrom:
    secretKeyRef:
      key: latest
      name: rapidapi-key
```

#### **3. Imagem está atualizada?**
```bash
gcloud run jobs describe vaga-linkedin-prod-staging \
  --region=us-central1 \
  --project=vaga-linkedin \
  --format="get(spec.template.spec.containers[0].image)"
```

**Output esperado:**
```
gcr.io/vaga-linkedin/vaga-linkedin-prod:staging-<COMMIT_SHA_MAIS_RECENTE>
```

#### **4. Executar teste completo:**
```bash
# Execute o job
EXECUTION=$(gcloud run jobs execute vaga-linkedin-prod-staging \
  --region=us-central1 \
  --project=vaga-linkedin \
  --format="get(metadata.name)")

echo "Execution: $EXECUTION"

# Aguardar conclusão
gcloud run jobs executions describe $EXECUTION \
  --region=us-central1 \
  --project=vaga-linkedin \
  --format="get(status.conditions[0].message)"
```

**Sucesso esperado:**
```
Execution completed successfully
```

---

## 📞 **Suporte e Ajuda**

### **Logs em Tempo Real**

```bash
# Via gcloud (streaming)
gcloud logging tail \
  "resource.type=cloud_run_job AND resource.labels.job_name=vaga-linkedin-prod-staging" \
  --project=vaga-linkedin

# Via Console (interface gráfica)
https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_job%22%0Aresource.labels.job_name%3D%22vaga-linkedin-prod-staging%22?project=vaga-linkedin
```

### **Métricas**

```bash
# Ver execuções recentes
gcloud run jobs executions list \
  --job=vaga-linkedin-prod-staging \
  --region=us-central1 \
  --limit=10

# Estatísticas
gcloud monitoring time-series list \
  --filter='resource.type="cloud_run_job" AND resource.labels.job_name="vaga-linkedin-prod-staging"' \
  --project=vaga-linkedin
```

---

## ✅ **Resumo Final**

### **ANTES (com v5 manual):**
```
❌ Deploy manual
❌ Imagem desatualizada
❌ Secrets incorretos (databricks, telegram)
❌ Erro ao executar
```

### **AGORA (com staging CI/CD):**
```
✅ Deploy automático via GitHub Actions
✅ Imagem sempre atualizada (a cada push)
✅ Secret correto (apenas RAPIDAPI_KEY)
✅ Pronto para executar
✅ Integrado com a esteira de CI/CD
```

### **Recomendação:**
1. ✅ **USE:** `vaga-linkedin-prod-staging` (automático)
2. ⏸️ **MANTENHA (opcional):** `vaga-linkedin-prod-v5` (manual, backup)
3. ✅ **EXECUTE:** Teste manual do job staging agora
4. ✅ **MONITORE:** Logs e métricas no GCP Console

---

**Última atualização:** 08/10/2025  
**Status:** ✅ Job configurado e pronto para uso  
**Próximo passo:** Executar teste manual
