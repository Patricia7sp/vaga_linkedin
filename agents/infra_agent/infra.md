# 🧠 Etapa 1 – infra_agent – Provisionamento da Infraestrutura

O objetivo desta etapa é preparar todo o ambiente necessário para o pipeline de dados, incluindo autenticações, instalações locais e criação de recursos no GCP e Databricks.

---

## 🎯 Objetivo Geral

Provisionar a infraestrutura necessária para o projeto:

1. Instalacao do pacote CLI do Google Cloud
2. Autenticação no GCP
3. Criação dos buckets no Cloud Storage
4. Autenticação com Terraform
5. Inicialização do projeto Terraform
6. Instalação e autenticação do Databricks CLI
6. Geração dos arquivos de configuração

---

## ✅ Etapas Detalhadas

### 📌 1. Autenticação no Google Cloud Platform (GCP)

- O agente deve solicitar login na sua conta GCP (via `gcloud auth login`).
- O projeto GCP será usado para armazenar dados extraídos do LinkedIn.
- Configurações necessárias:
  - Definir ID do projeto
  - Selecionar região (ex: `us-central1`)
  - Habilitar APIs necessárias (Cloud Storage, IAM, etc.)

**Comandos esperados:**
```bash
gcloud auth login
gcloud config set project [PROJECT_ID]
gcloud services enable storage.googleapis.com


### 📌 2. Criação dos buckets no Cloud Storage

Nome sugerido: linkedin-dados-raw, linkedin-dados-processados

- O agente deve criar os buckets no Cloud Storage para armazenar os dados brutos e tratados.
- O bucket deve ser criado com a seguinte estrutura:
  - `linkedin-dados-raw`: para armazenar os dados brutos extraídos do LinkedIn.
  - `linkedin-dados-processados`: para armazenar os dados tratados no Databricks.
Configurações:
Classe de armazenamento: STANDARD
Localização: us-central1


**Comandos esperados:**
```bash
gcloud storage buckets create [BUCKET_NAME] --location [REGION]
gcloud storage buckets create linkedin-dados-raw --location us-central1
gcloud storage buckets create linkedin-dados-processados --location us-central1
```

### 📌 3. Autenticação com Terraform

Instalação e Autenticação do Terraform
O agente deverá verificar se o Terraform está instalado. Caso não, solicitar instalação.
Após instalação, inicializar projeto Terraform localmente.
Autenticação:
Pode ser feita via token OAuth ou login com conta do Gmail, se disponível.
Caso não seja possível, o agente deve instruir a criar uma conta no Terraform Cloud.

- O agente deve autenticar com Terraform para que possa criar os recursos no GCP.
- O agente deve solicitar login na sua conta GCP (via `gcloud auth login`).


**Comandos esperados:**
```bash
gcloud auth login
```

### 📌 4. Instalação e autenticação do Databricks CLI

- O agente deve instalar o Databricks CLI e autenticar com ele para que possa criar os recursos no Databricks.
- O agente deve solicitar login na sua conta Databricks (via `databricks auth login`).

**Comandos esperados:**
```bash
databricks auth login
```
- Instalar o Databricks CLI (v0.x ou v1.x).
- Solicitar ao usuário um token de acesso pessoal do Databricks.
- Configurar o perfil no terminal.




