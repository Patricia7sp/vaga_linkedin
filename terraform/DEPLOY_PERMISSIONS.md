# 🔐 Configuração de Permissões IAM para Deploy

Este documento explica como aplicar as permissões IAM necessárias para que a service account `linkedin-scraper@vaga-linkedin.iam.gserviceaccount.com` possa realizar deploys via CI/CD.

## 📋 Permissões Adicionadas

O arquivo `gcp_services.tf` foi atualizado com as seguintes permissões para a service account:

| Role | Descrição | Para que serve |
|------|-----------|----------------|
| `roles/run.admin` | Cloud Run Admin | Criar e atualizar Cloud Run jobs |
| `roles/cloudbuild.builds.editor` | Cloud Build Editor | Executar builds de imagens Docker |
| `roles/iam.serviceAccountUser` | Service Account User | Atuar como service account |
| `roles/artifactregistry.writer` | Artifact Registry Writer | Push de imagens Docker |
| `roles/storage.objectAdmin` | Storage Object Admin | Gerenciar objetos no GCS |
| `roles/secretmanager.secretAccessor` | Secret Manager Accessor | Acessar secrets no deploy |

## 🚀 Como Aplicar (Via Terraform)

### **Pré-requisitos:**
1. Terraform instalado
2. Credenciais GCP configuradas (`gcloud auth login`)
3. Variáveis configuradas em `terraform.tfvars`

### **Passos:**

1. **Navegue até o diretório Terraform:**
   ```bash
   cd terraform/
   ```

2. **Crie/edite o arquivo `terraform.tfvars`:**
   ```hcl
   # Habilitar gerenciamento de recursos GCP
   manage_gcp_resources = true
   
   # Projeto GCP
   gcp_project_id = "vaga-linkedin"
   gcp_region     = "us-central1"
   
   # Service Account (já tem default no variables.tf)
   gcp_service_account_email = "linkedin-scraper@vaga-linkedin.iam.gserviceaccount.com"
   
   # Outras variáveis necessárias...
   databricks_host   = "https://..."
   databricks_token  = "..."
   current_user_email = "seu-email@gmail.com"
   ```

3. **Inicialize o Terraform (se ainda não fez):**
   ```bash
   terraform init
   ```

4. **Verifique o que será criado:**
   ```bash
   terraform plan
   ```

5. **Aplique as mudanças:**
   ```bash
   terraform apply
   ```
   
   Digite `yes` quando solicitado.

6. **Verifique se foi aplicado:**
   ```bash
   terraform show | grep "sa_run_admin" -A 5
   ```

## 🛠️ Como Aplicar (Manualmente via Console GCP)

Se preferir não usar Terraform, pode aplicar manualmente:

1. **Acesse o Console GCP:**
   - https://console.cloud.google.com/iam-admin/iam

2. **Encontre a service account:**
   - `linkedin-scraper@vaga-linkedin.iam.gserviceaccount.com`

3. **Adicione os roles clicando em "Edit" (lápis):**
   - Cloud Run Admin
   - Cloud Build Editor
   - Service Account User
   - Artifact Registry Writer
   - Storage Object Admin
   - Secret Manager Secret Accessor

4. **Salve as alterações**

## 🛠️ Como Aplicar (Via gcloud CLI)

Alternativamente, use o CLI:

```bash
# Variáveis
PROJECT_ID="vaga-linkedin"
SA_EMAIL="linkedin-scraper@vaga-linkedin.iam.gserviceaccount.com"

# Adicionar roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

## ✅ Verificação

Após aplicar as permissões, execute um novo deploy via GitHub Actions:

```bash
# Trigger manual do pipeline
git commit --allow-empty -m "test: verificar permissoes IAM"
git push
```

O stage **🎭 Deploy to Staging** deve passar agora! 🎉

## 🔒 Segurança

**IMPORTANTE:** Estas permissões seguem o princípio do menor privilégio necessário para CI/CD. A service account tem acesso apenas ao necessário para deploy de aplicações.

## 📚 Referências

- [Google Cloud Run IAM](https://cloud.google.com/run/docs/securing/managing-access)
- [Cloud Build IAM](https://cloud.google.com/build/docs/iam-roles-permissions)
- [Service Accounts Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)
