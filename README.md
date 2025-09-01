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

## 🚧 Status Inicial

- [ ] Etapa 1: Infraestrutura – **em preparação**
- [ ] Etapa 2: Extração Streaming – **aguardando infraestrutura**
- [ ] Etapa 3: Armazenamento – **aguardando dados**
- [ ] Etapa 4: Integração com Databricks – **pendente**
- [ ] Etapa 5: Transformação – **pendente**
- [ ] Etapa 6: Visualização – **em planejamento**
- [ ] Etapa 7: Orquestração com IA – **em desenvolvimento**

---

## 📎 Observações

- O projeto é de cunho pessoal e visa aprendizado com tecnologias de dados em ambiente realista.
- A plataforma LinkedIn será utilizada como fonte de dados respeitando seus termos de uso.

---

