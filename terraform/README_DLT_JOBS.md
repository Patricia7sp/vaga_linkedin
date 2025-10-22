# 🚀 Terraform - DLT Jobs Automation

## 📌 O que este módulo faz?

Cria **automaticamente** os 3 jobs do Databricks para executar os pipelines DLT:

1. ✅ `dlt-data-engineer-pipeline`
2. ✅ `dlt-data-analytics-pipeline`
3. ✅ `dlt-digital-analytics-pipeline`

**Vantagens:**
- ✅ **Infraestrutura como Código** (versionada no Git)
- ✅ **Sem criação manual** via UI
- ✅ **Consistente e reproduzível**
- ✅ **Fácil gerenciar** (update, destroy)

---

## 📋 Pré-requisitos

### 1. Terraform instalado
```bash
# Verificar instalação
terraform version

# Se não instalado (Mac):
brew install terraform

# Ou baixar: https://www.terraform.io/downloads
```

### 2. Credenciais Databricks
```bash
# Obter token: Databricks UI → Settings → Developer → Access Tokens
export DATABRICKS_HOST="https://dbc-14d16b60-2882.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi..."
```

---

## 🚀 Como usar

### **Passo 1: Configurar ambiente**

```bash
cd /usr/local/anaconda3/vaga_linkedin/terraform/

# Exportar credenciais
export DATABRICKS_HOST="https://dbc-14d16b60-2882.cloud.databricks.com"
export DATABRICKS_TOKEN="seu-token-aqui"
```

### **Passo 2: Inicializar Terraform**

```bash
terraform init
```

**Output esperado:**
```
Initializing the backend...
Initializing provider plugins...
- Finding databricks/databricks versions matching "~> 1.29"...
- Installing databricks/databricks v1.29.0...

Terraform has been successfully initialized!
```

### **Passo 3: Planejar mudanças (preview)**

```bash
terraform plan -target=databricks_job.dlt_pipeline_jobs
```

**Output esperado:**
```
Terraform will perform the following actions:

  # databricks_job.dlt_pipeline_jobs["data_engineer"] will be created
  + resource "databricks_job" "dlt_pipeline_jobs" {
      + name     = "dlt-data-engineer-pipeline"
      + schedule = {
          + quartz_cron_expression = "0 30 8,12,21 ? * MON-FRI"
          + timezone_id            = "America/Sao_Paulo"
        }
      ...
    }

  # databricks_job.dlt_pipeline_jobs["data_analytics"] will be created
  ...

  # databricks_job.dlt_pipeline_jobs["digital_analytics"] will be created
  ...

Plan: 3 to add, 0 to change, 0 to destroy.
```

### **Passo 4: Aplicar (criar jobs)**

```bash
terraform apply -target=databricks_job.dlt_pipeline_jobs
```

**Confirmar:**
```
Do you want to perform these actions?
  Enter a value: yes
```

**Output esperado:**
```
databricks_job.dlt_pipeline_jobs["data_engineer"]: Creating...
databricks_job.dlt_pipeline_jobs["data_analytics"]: Creating...
databricks_job.dlt_pipeline_jobs["digital_analytics"]: Creating...

databricks_job.dlt_pipeline_jobs["data_engineer"]: Creation complete after 2s [id=123456789]
databricks_job.dlt_pipeline_jobs["data_analytics"]: Creation complete after 2s [id=234567890]
databricks_job.dlt_pipeline_jobs["digital_analytics"]: Creation complete after 2s [id=345678901]

Apply complete! Resources: 3 added, 0 changed, 0 destroyed.

Outputs:

dlt_job_ids = {
  "data_analytics" = "234567890"
  "data_engineer" = "123456789"
  "digital_analytics" = "345678901"
}

dlt_job_urls = {
  "data_analytics" = "https://dbc-14d16b60-2882.cloud.databricks.com/#job/234567890"
  "data_engineer" = "https://dbc-14d16b60-2882.cloud.databricks.com/#job/123456789"
  "digital_analytics" = "https://dbc-14d16b60-2882.cloud.databricks.com/#job/345678901"
}
```

### **Passo 5: Validar no Databricks UI**

1. Acessar: https://dbc-14d16b60-2882.cloud.databricks.com/
2. Menu → **Workflows**
3. Verificar 3 novos jobs criados:
   - ✅ `dlt-data-engineer-pipeline`
   - ✅ `dlt-data-analytics-pipeline`
   - ✅ `dlt-digital-analytics-pipeline`

---

## 📊 Estrutura criada

```
DATABRICKS JOBS (via Terraform):

┌─────────────────────────────────────────┐
│  dlt-data-engineer-pipeline             │
│  ├─ Schedule: 08:30, 12:30, 21:30      │
│  ├─ Notebook: linkedin_pipeline_runner  │
│  ├─ Parâmetro: pipeline=data_engineer   │
│  └─ Tags: pipeline, type, domain        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  dlt-data-analytics-pipeline            │
│  ├─ Schedule: 09:00, 13:00, 22:00      │
│  ├─ Notebook: linkedin_pipeline_runner  │
│  ├─ Parâmetro: pipeline=data_analytics  │
│  └─ Tags: pipeline, type, domain        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  dlt-digital-analytics-pipeline         │
│  ├─ Schedule: 10:00, 14:00, 23:00      │
│  ├─ Notebook: linkedin_pipeline_runner  │
│  ├─ Parâmetro: pipeline=digital_analytics│
│  └─ Tags: pipeline, type, domain        │
└─────────────────────────────────────────┘
```

---

## 🔧 Operações comuns

### **Ver IDs dos jobs criados**

```bash
terraform output dlt_job_ids
```

### **Ver URLs dos jobs**

```bash
terraform output dlt_job_urls
```

### **Atualizar configuração de 1 job**

1. Editar `terraform/databricks_dlt_jobs.tf`
2. Exemplo: Mudar horário do data_engineer:
   ```hcl
   data_engineer = {
     ...
     cron = "0 0 9 ? * MON-FRI"  # Novo horário: 09:00
   }
   ```
3. Aplicar mudança:
   ```bash
   terraform apply -target=databricks_job.dlt_pipeline_jobs[\"data_engineer\"]
   ```

### **Pausar job via Terraform**

```hcl
schedule {
  ...
  pause_status = "PAUSED"  # UNPAUSED → PAUSED
}
```

```bash
terraform apply -target=databricks_job.dlt_pipeline_jobs[\"data_engineer\"]
```

### **Deletar jobs**

```bash
# Deletar apenas jobs DLT
terraform destroy -target=databricks_job.dlt_pipeline_jobs

# Ou deletar tudo (cuidado!)
terraform destroy
```

---

## ⚠️ Troubleshooting

### **Erro: "Organization has been cancelled or is not active yet"**

**Causa:** Daily limit exhausted (temporário)

**Solução:**
1. ✅ Aguardar 24h para reset
2. ✅ Tentar novamente
3. ✅ Terraform retenta automaticamente

### **Erro: "DATABRICKS_HOST not set"**

**Solução:**
```bash
export DATABRICKS_HOST="https://dbc-14d16b60-2882.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi..."
```

### **Erro: "Invalid token"**

**Solução:**
1. Databricks UI → Settings → Developer → Access Tokens
2. Criar novo token
3. Exportar: `export DATABRICKS_TOKEN="novo-token"`

### **Jobs não aparecem no UI**

**Solução:**
```bash
# Verificar se foram criados
terraform show | grep databricks_job

# Ver state
terraform state list | grep dlt_pipeline_jobs

# Ver output
terraform output dlt_job_ids
```

---

## 🎯 Vantagens vs Criação Manual (UI)

| Aspecto | Terraform ✅ | UI Manual ❌ |
|---------|-------------|-------------|
| **Tempo** | 2 minutos (1 comando) | 15 minutos (3 jobs) |
| **Erros** | Zero (validado) | Possíveis (digitação) |
| **Versionamento** | Git (histórico) | Nenhum |
| **Reproduzível** | 100% | Depende de quem cria |
| **Rollback** | `terraform destroy` | Manual (deletar 1 por 1) |
| **Documentação** | Código é doc | Precisa documentar separado |
| **CI/CD** | Integra fácil | Difícil automatizar |
| **Auditoria** | Git log | Nenhuma |

---

## 📝 Arquivos Terraform

```
terraform/
├── databricks_dlt_jobs.tf     ← NOVO - Jobs DLT (este módulo)
├── databricks_dlt.tf          ← Pipelines DLT (existente)
├── databricks_files.tf        ← Notebooks (existente)
├── agent_chat.tf              ← Job Agent Chat (existente)
├── main.tf                    ← Provider config
├── variables.tf               ← Variáveis
└── README_DLT_JOBS.md         ← Este guia
```

---

## 🔒 Segurança

### **NÃO commitar tokens no Git:**

```bash
# ❌ NUNCA fazer isso:
export DATABRICKS_TOKEN="dapi123..."
git add .
git commit -m "add token"  # ❌ ERRADO!

# ✅ SEMPRE usar variável de ambiente:
export DATABRICKS_TOKEN="dapi..."  # Apenas na sessão local
terraform apply
```

### **Usar GitHub Secrets para CI/CD:**

```yaml
# .github/workflows/terraform.yml
env:
  DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
  DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
```

---

## 🚀 Próximos Passos

### **1. Testar jobs criados**

Após criar via Terraform, testar manualmente:

```bash
# Databricks UI → Workflows → Selecionar job → "Run now"
```

Validar:
- ✅ Duration: 9-11 minutos (não 1 minuto!)
- ✅ Status: SUCCESS
- ✅ Logs mostram pipeline correto executado

### **2. Monitorar execuções**

```bash
# Ver últimas runs
databricks jobs list-runs --job-id <job_id> --limit 5
```

### **3. Integrar com CI/CD**

Criar workflow GitHub Actions:

```yaml
name: Terraform Deploy Jobs

on:
  push:
    branches: [main]
    paths:
      - 'terraform/databricks_dlt_jobs.tf'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: hashicorp/setup-terraform@v2
      - name: Terraform Apply
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
        run: |
          cd terraform
          terraform init
          terraform apply -target=databricks_job.dlt_pipeline_jobs -auto-approve
```

---

## ✅ Checklist de Deploy

Antes de aplicar Terraform:

- [ ] Credenciais configuradas (`DATABRICKS_HOST`, `DATABRICKS_TOKEN`)
- [ ] Daily limit resetado (aguardar 24h se necessário)
- [ ] Notebook deployado (`/Shared/linkedin_pipeline_runner_notebook`)
- [ ] Pipelines DLT existem (data_engineer, data_analytics, digital_analytics)
- [ ] `terraform init` executado
- [ ] `terraform plan` revisado
- [ ] Backup do state (`terraform.tfstate`)

Após aplicar:

- [ ] Verificar outputs (`terraform output`)
- [ ] Validar jobs no Databricks UI
- [ ] Testar 1 job manualmente
- [ ] Verificar logs e duration
- [ ] Ativar schedule se desabilitado

---

## 📚 Referências

- [Terraform Databricks Provider](https://registry.terraform.io/providers/databricks/databricks/latest/docs)
- [Databricks Job Resource](https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/job)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)

---

**🎉 Terraform é a forma CORRETA e PROFISSIONAL de gerenciar infraestrutura Databricks!**

**Muito mais rápido, seguro e confiável que criação manual via UI! 🚀**
