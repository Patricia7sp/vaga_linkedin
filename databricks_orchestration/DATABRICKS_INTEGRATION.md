# Configuração de Integração Git no Databricks

## 🔗 Conectando o Repositório GitHub ao Databricks

### Passo 1: Configurar Integração Git no Databricks

1. **Acesse o Admin Console:**
   - No Databricks Workspace, vá para **Admin Console**
   - Clique em **Git Integration** (no menu lateral esquerdo)

2. **Adicionar Repositório GitHub:**
   - Clique em **Add Git repository**
   - Preencha os campos:
     - **Name**: `vagas_linkedin_terraform`
     - **Git provider**: GitHub
     - **Git URL**: `https://github.com/SEU_USERNAME/vagas_linkedin.git`
     - **Branch**: `main` (ou a branch que você usa)
     - **Path**: `/databricks_orchestration` (apenas a pasta Terraform)

3. **Configurar Credenciais:**
   - Use **Personal Access Token** do GitHub
   - Vá para GitHub → Settings → Developer settings → Personal access tokens
   - Crie um token com as permissões: `repo`, `workflow`

### Passo 2: Criar Git Folder no Databricks

1. **No Workspace:**
   - Clique em **Workspace** no menu lateral
   - Clique em **Create** → **Git folder**

2. **Configurar o Git Folder:**
   - **Name**: `Terraform_Orchestration`
   - Selecione o repositório configurado no passo anterior
   - **Path in repository**: `/databricks_orchestration`
   - **Branch**: `main`

### Passo 3: Trabalhando com Terraform via Databricks

1. **Acesse o Git Folder:**
   - Vá para o Git Folder criado
   - Você verá todos os arquivos Terraform

2. **Editar e Versionar:**
   - Edite os arquivos diretamente no Databricks
   - As mudanças são automaticamente commitadas para o GitHub
   - Use branches para diferentes ambientes (dev, staging, prod)

3. **Executar Terraform:**
   - Crie um Notebook Python no Databricks
   - Use o comando mágico `%sh` para executar Terraform:

```python
%sh
cd /Workspace/Users/SEU_USERNAME/Terraform_Orchestration
terraform init
terraform plan
terraform apply
```

### Passo 4: Configurar Secrets para Tokens

1. **No Databricks:**
   - Vá para **Manage** → **Secrets**
   - Crie um scope: `terraform_secrets`

2. **Adicionar Secrets:**
   - `databricks_token`: Seu token do Databricks
   - `aws_access_key_id`: Chave de acesso AWS (se aplicável)
   - `aws_secret_access_key`: Chave secreta AWS (se aplicável)

3. **Usar no Terraform:**
   ```hcl
   # No terraform.tfvars
   databricks_token = "{{secrets/terraform_secrets/databricks_token}}"
   ```

## 🚀 Workflow Recomendado

### Desenvolvimento Local → GitHub → Databricks

1. **Desenvolvimento Local:**
   ```bash
   # Edite arquivos localmente
   cd databricks_orchestration
   terraform validate
   terraform plan
   ```

2. **Commit para GitHub:**
   ```bash
   git add .
   git commit -m "feat: update terraform configuration"
   git push origin main
   ```

3. **Deploy via Databricks:**
   - As mudanças aparecem automaticamente no Git Folder
   - Execute `terraform apply` através de um Job ou Notebook

### Usando Jobs do Databricks para Automação

1. **Criar um Job:**
   - **Task type**: Python
   - **Source**: Git provider
   - **Git repository URL**: Seu repositório
   - **Git reference**: Branch ou tag

2. **Script de Execução:**
   ```python
   import subprocess
   import os

   # Configurar ambiente
   os.chdir('/Workspace/Users/SEU_USERNAME/Terraform_Orchestration')

   # Executar Terraform
   commands = [
       'terraform init',
       'terraform validate',
       'terraform plan -out=tfplan',
       'terraform apply tfplan'
   ]

   for cmd in commands:
       result = subprocess.run(cmd.split(), capture_output=True, text=True)
       print(f"Executando: {cmd}")
       print(f"STDOUT: {result.stdout}")
       print(f"STDERR: {result.stderr}")
       if result.returncode != 0:
           raise Exception(f"Falha no comando: {cmd}")
   ```

## 📋 Próximos Passos

- [ ] Configurar integração Git no Databricks
- [ ] Criar Git Folder para a pasta `databricks_orchestration`
- [ ] Configurar secrets para tokens sensíveis
- [ ] Criar Job automatizado para deploy do Terraform
- [ ] Testar o workflow completo

## ⚠️ Considerações de Segurança

- Nunca commite arquivos com tokens ou chaves reais
- Use sempre secrets do Databricks para dados sensíveis
- Configure permissões mínimas necessárias no GitHub token
- Use branches separadas para diferentes ambientes
- Faça code reviews antes de aplicar mudanças em produção
