# Databricks Orchestration - Unity Catalog

Este diretório contém a infraestrutura como código (IaC) para provisionamento e gerenciamento do Unity Catalog no Databricks usando Terraform.

## 📁 Estrutura

```
databricks_orchestration/
├── providers.tf          # Configuração do provider Databricks
├── main.tf              # Recursos Unity Catalog (catálogos, schemas, credenciais, etc.)
├── variables.tf         # Definição de variáveis
└── terraform.tfvars.example  # Exemplo de configuração
```

## 🚀 Como Usar

### 1. Pré-requisitos

- Terraform v1.0+
- Acesso ao workspace Databricks
- Token de acesso Databricks
- Conta AWS com IAM roles configuradas (se aplicável)

### 2. Configuração

1. **Copie o arquivo de exemplo:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edite o `terraform.tfvars` com seus valores:**
   ```hcl
   databricks_host  = "https://your-workspace.cloud.databricks.com"
   databricks_token = "your-databricks-token-here"
   catalog_name     = "vagas_linkedin_catalog"
   # ... outros valores
   ```

### 3. Inicialização e Aplicação

```bash
# Inicializar Terraform
terraform init

# Validar configuração
terraform validate

# Planejar mudanças
terraform plan

# Aplicar mudanças
terraform apply
```

## 📋 Recursos Provisionados

### Unity Catalog
- **Catálogo**: `vagas_linkedin_catalog`
- **Schema**: `bronze`
- **Credenciais de Storage**: Para acesso ao S3
- **Localizações Externas**: Para dados no S3
- **Permissões**: Grants para `data_scientists` e `data_readers`

### Permissões Configuradas

#### Catálogo
- `data_scientists`: USE_CATALOG, BROWSE, CREATE_SCHEMA
- `data_readers`: USE_CATALOG, BROWSE

#### Schema Bronze
- `data_scientists`: USE_SCHEMA, CREATE_TABLE, CREATE_VIEW, CREATE_FUNCTION, MODIFY, SELECT
- `data_readers`: USE_SCHEMA, SELECT

## 🔧 Personalização

### Adicionar Novos Schemas

```hcl
resource "databricks_schema" "silver" {
  name         = "silver"
  catalog_name = databricks_catalog.sales.name
  comment      = "Schema silver"
}
```

### Configurar Permissões Adicionais

```hcl
resource "databricks_grants" "schema_silver" {
  schema = "${databricks_catalog.sales.name}.${databricks_schema.silver.name}"

  grant {
    principal  = "analysts"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}
```

## 🔄 Integração com GitHub

Para conectar este repositório ao Databricks:

1. **No Databricks Workspace:**
   - Vá para Admin Console > Git Integration
   - Adicione este repositório GitHub
   - Configure as permissões necessárias

2. **Para versionamento:**
   - Mantenha o código Terraform versionado
   - Use branches para diferentes ambientes
   - Faça code reviews antes de aplicar mudanças

## 🛡️ Segurança

- Nunca commite o arquivo `terraform.tfvars` (contém tokens sensíveis)
- Use variáveis de ambiente ou secrets do Databricks para tokens
- Configure permissões mínimas necessárias (princípio do menor privilégio)

## 📝 Próximos Passos

- [ ] Configurar ambiente de desenvolvimento
- [ ] Configurar ambiente de produção
- [ ] Adicionar schemas `silver` e `gold`
- [ ] Configurar SQL Warehouses
- [ ] Configurar Jobs para processamento de dados
