# Projeto: Coleta e Processamento de Vagas do LinkedIn - Área de Dados

## 🎯 Objetivo Geral

Construir um pipeline automatizado e escalável para coletar, armazenar, transformar e visualizar vagas da área de dados (Engenharia de Dados, Análise de Dados, etc.) publicadas no LinkedIn. O pipeline será desenvolvido com foco em aprendizado prático e uso de tecnologias modernas de dados e IA.

---

## 🧩 Tecnologias Envolvidas

- **PySpark** – Processamento de dados em larga escala.
- **Apache Kafka** – Ingestão de dados em streaming.
- **Google Cloud Storage (GCP)** – Armazenamento de dados brutos e tratados.
- **Databricks (via CLI)** – Manipulação, transformação e análise dos dados.
- **Terraform** – Provisionamento da infraestrutura como código.
- **Agentes de IA** – Multi-agentes com responsabilidades específicas.
- **LinkedIn** – Fonte de dados (vagas).
- **Dashboards (Databricks ou externos)** – Visualização dos insights.

---

## 🧠 Arquitetura de Agentes IA

O projeto será assistido por agentes de IA especializados, cada um com sua função:

- `infra_agent`: Provisiona a infraestrutura com Terraform.
- `extract_agent`: Extrai as vagas do LinkedIn e envia ao Kafka.
- `load_agent`: Carrega dados do Storage para o Databricks.
- `transform_agent`: Processa e modela os dados no Databricks.
- `viz_agent`: Gera dashboards com base nos dados tratados.
- `control_agent`: Orquestra todas as etapas e validações do projeto.

---

## 🧱 Etapas do Projeto

### ✅ Etapa 1: Infraestrutura
- **Tecnologias:** Terraform, GCP, Databricks
- **Objetivos:**
  - Criar buckets no Cloud Storage.
  - Criar o workspace e configs no Databricks.
  - Conceder permissões entre Databricks e GCP.
- **Agente responsável:** `infra_agent`

---

### ✅ Etapa 2: Extração de Vagas do LinkedIn (Streaming)
- **Tecnologias:** Kafka, PySpark, LinkedIn
- **Objetivos:**
  - Configurar Kafka para receber dados em tempo real.
  - Criar script PySpark Structured Streaming.
- **Agente responsável:** `extract_agent`

---

### ✅ Etapa 3: Armazenamento no Cloud Storage
- **Tecnologias:** GCP Cloud Storage
- **Objetivos:**
  - Gravar os dados extraídos em JSON ou Parquet.
  - Organizar os dados por data e tipo de vaga.
- **Agente responsável:** `extract_agent`

---

### ✅ Etapa 4: Integração com Databricks via CLI
- **Tecnologias:** Databricks CLI, PySpark
- **Objetivos:**
  - Conectar o Storage ao Databricks.
  - Carregar os dados para análise.
- **Agente responsável:** `load_agent`

---

### ✅ Etapa 5: Transformação dos Dados
- **Tecnologias:** PySpark no Databricks
- **Objetivos:**
  - Limpeza e modelagem dos dados.
  - Criação de tabelas organizadas (vaga, empresa, localização etc.).
- **Agente responsável:** `transform_agent`

---

### ✅ Etapa 6: Visualização dos Dados
- **Tecnologias:** Dashboards do Databricks ou externos (Power BI, Looker etc.)
- **Objetivos:**
  - Visualizar principais métricas: quantidade de vagas, empresas, tecnologias exigidas etc.
- **Agente responsável:** `viz_agent`

---

### ✅ Etapa 7: Orquestração e Validação com Agentes IA
- **Tecnologias:** API + Prompt Engineering + Agentes IA
- **Objetivos:**
  - Cada etapa será aprovada manualmente pelo usuário antes de continuar.
  - O `control_agent` garantirá a sequência correta entre as etapas.

---

## 📌 Forma de Execução

1. Cada etapa será ativada manualmente pelo usuário.
2. Após validação, o agente `control_agent` libera o avanço para a próxima fase.
3. O projeto será iterativo e orientado por feedback incremental.

---

## 🏆 Conquistas e Resultados Técnicos

### ✅ **Pipeline de Dados End-to-End Funcional**
Desenvolvido e implementado com sucesso um sistema completo de extração, processamento e armazenamento de dados em tempo real, demonstrando competências avançadas em:

- **🏗️ Arquitetura de Dados Moderna:** Infraestrutura cloud-native no Google Cloud Platform com Service Accounts e IAM configurados
- **⚡ Streaming de Dados em Tempo Real:** Apache Kafka + Zookeeper + PySpark Structured Streaming operacional
- **☁️ Integração Cloud:** Sincronização automática com Google Cloud Storage, dados organizados e versionados
- **🤖 Engenharia de IA:** Sistema multi-agentes implementado para orquestração inteligente do pipeline

### 🎯 **Competências Técnicas Demonstradas**
- **Engenharia de Dados:** PySpark, Apache Kafka, Data Streaming, ETL/ELT
- **Cloud Computing:** Google Cloud Platform, Storage, IAM, Service Accounts  
- **DevOps & Infraestrutura:** Terraform, Docker, Automação de Deploy
- **Inteligência Artificial:** Agentes autônomos, Prompt Engineering, Automação Inteligente
- **Desenvolvimento:** Python, Selenium, APIs, Microserviços

### 🚀 **Próximos Marcos**
- Integração com Databricks para análises avançadas
- Dashboards e visualizações de dados interativas
- Expansão do sistema para outras fontes de dados

---

## ⚙️ Configuração e Pré-requisitos

### Dependências Necessárias
- Python 3.8+
- Apache Kafka e Zookeeper
- Google Cloud SDK (gcloud CLI)
- Java 8+ (para Kafka/Spark)
- Selenium WebDriver

### Configuração do Ambiente

1. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   brew install kafka zookeeper  # macOS
   ```

2. **Configurar serviços:**
   ```bash
   brew services start zookeeper
   brew services start kafka
   ```

3. **Configurar credenciais GCP:**
   ```bash
   # Criar Service Account no GCP Console
   gcloud iam service-accounts create linkedin-scraper
   gcloud iam service-accounts keys create gcp-credentials.json --iam-account=linkedin-scraper@[PROJECT-ID].iam.gserviceaccount.com
   ```

4. **Configurar arquivo .env:**
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json
   GCP_BUCKET_NAME=linkedin-dados-raw
   GCP_PROJECT_ID=vaga-linkedin
   KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   KAFKA_TOPIC=vagas_dados
   ```

---

## 🚀 Como Executar

### Execução Completa (Modo Streaming + GCP)
```bash
python main.py
```

### Execução Apenas Extração (Modo Offline)
```bash
python run_extraction_only.py
```

### Verificar Status dos Serviços
```bash
# Verificar Kafka/Zookeeper
brew services list | grep -E "(kafka|zookeeper)"

# Verificar autenticação GCP
gcloud auth list
export GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json
gcloud auth application-default print-access-token
```

---

## 📊 Resultados Obtidos

### Pipeline Funcional
- ✅ **Extração automatizada** de vagas do LinkedIn (6 categorias)
- ✅ **Processamento em tempo real** via Kafka/PySpark
- ✅ **Armazenamento na nuvem** (GCP Cloud Storage)
- ✅ **Dados estruturados** em formato JSONL organizados por data

### Dados Coletados
- **Categorias:** Data Engineer, Data Analytics, Digital Analytics
- **Campos extraídos:** título, empresa, localização, descrição, skills, salário
- **Volume:** ~6 vagas por execução (limitado para testes)
- **Formato:** JSONL com estrutura padronizada

### Arquitetura Implementada
```
LinkedIn → Selenium → Kafka → PySpark → GCP Storage
                              ↓
                         Processamento
                         + Enriquecimento
```

---

## 📎 Observações

- O projeto é de cunho pessoal e visa aprendizado com tecnologias de dados em ambiente realista.
- A plataforma LinkedIn será utilizada como fonte de dados respeitando seus termos de uso.

---

