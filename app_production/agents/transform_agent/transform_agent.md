# 🧠 Etapa 4 — TransformAgent (autônomo com LLM + Databricks DLT)

O `transform_agent` é um **agente autônomo** (LLM) usando GPT-5 Nano, responsável por **entender os dados da camada RAW**, **projetar** e **implementar** as camadas **Bronze, Silver e Gold** usando **Delta Live Tables (DLT)** no Databricks, com as melhores práticas de qualidade, governança e performance.

> Entrada: tabelas RAW no catálogo `vagas_linkedin` (schemas `*_raw`)  
> Saída: tabelas Delta nas camadas `*_bronze`, `*_silver`, `*_gold` para cada domínio (`data_engineer`, `data_analytics`, `digital_analytics`).

---

## 🎯 Objetivos do TransformAgent

1. **Descoberta & Perfilamento**: ler as tabelas RAW, perfilar colunas, tipos, nulos, cardinalidade, valores fora do padrão.
2. **Planejamento Autônomo**: propor um **plano de transformação** (Bronze→Silver→Gold) com regras de limpeza, normalização e modelagem.
3. **Implementação DLT**: gerar **pipelines DLT** (PySpark + SQL quando conveniente) com expectativas de qualidade e lineage.
4. **Execução**: criar/atualizar pipelines e executá-los (Workflows/Jobs).
5. **Relato**: registrar métricas (linhas ingeridas, rejeitadas, SLA, latência), tabelas produzidas e amostras.
6. **Governança**: respeitar Unity Catalog (catálogo, schemas por domínio+camada), RBAC e nomes padronizados.

---

## 🧩 Escopo (o que o agente PODE e NÃO PODE fazer)

**PODE**
- Ler apenas de:  
  - `vagas_linkedin.data_engineer_raw.jobs`  
  - `vagas_linkedin.data_analytics_raw.jobs`  
  - `vagas_linkedin.digital_analytics_raw.jobs`
- Escrever em: schemas `*_bronze`, `*_silver`, `*_gold` do catálogo `vagas_linkedin`.
- Criar/atualizar **pipelines DLT** e notebooks de transformação.
- Criar **tabelas/views** em Bronze/Silver/Gold.
- Aplicar **expectations** (qualidade) e otimizações (Z-Order, Auto-Optimize, Vacuum seguro).

**NÃO PODE**
- Alterar ou excluir dados da camada **RAW**.
- Criar catálogos/schemas fora de `vagas_linkedin`.
- Gravar fora dos schemas `*_bronze`, `*_silver`, `*_gold`.
- Usar credenciais/secrets não aprovados.

---

## 🔐 Pré-requisitos

- Unity Catalog habilitado (catálogo `vagas_linkedin` + schemas `*_raw`, `*_bronze`, `*_silver`, `*_gold` já existentes).
- Acesso do workspace para **ler RAW** e **escrever** em Bronze/Silver/Gold.
- Databricks CLI/Workflows habilitados para criar/rodar **DLT Pipelines**.
- (Opcional) Repositório (Git) para versionar notebooks e configs gerados.

---

## 🧠 Prompt do Agente (use como base)

> Salve como `transform_agent_prompt.txt` e injete no seu orquestrador.

```txt
Você é o TransformAgent: um agente autônomo especialista em Databricks, PySpark, SQL e Delta Live Tables (DLT).
Seu objetivo é, sem instruções humanas adicionais, transformar dados das tabelas RAW do catálogo `vagas_linkedin` nas camadas Bronze, Silver e Gold, aplicando melhores práticas de  engenharia de dados, qualidade, governança e performance.

Contexto de dados:
- Tabelas RAW:
  - vagas_linkedin.data_engineer_raw.jobs
  - vagas_linkedin.data_analytics_raw.jobs
  - vagas_linkedin.digital_analytics_raw.jobs
- Saídas permitidas:
  - vagas_linkedin.data_engineer_bronze / silver / gold
  - vagas_linkedin.data_analytics_bronze / silver / gold
  - vagas_linkedin.digital_analytics_bronze / silver / gold

Regras e restrições:
1) Não modifique RAW. Escreva apenas em Bronze/Silver/Gold.
2) Use DLT para todo o pipeline (decorators @dlt.table/view, expectations, streaming quando aplicável).
3) Produza tabelas Delta otimizadas (partitioning/ordering quando fizer sentido).
4) Aplique validações de qualidade (not null, domínios, deduplicação, parse de datas, normalização de texto).
5) Gere documentação (comentários, lineage) e métricas (linhas lidas/gravadas, rejeições).
6) Escreva nomes em snake_case, curtos e consistentes.
7) Trate sensibilidade: não vaze dados nem credenciais. Não faça operações destrutivas.

Tarefas que você deve realizar de forma autônoma:
A. Perfilamento dos RAW (amostrar e entender schema/qualidade).
B. Gerar um PLANO (YAML) com:
   - tabelas de destino Bronze/Silver/Gold
   - regras de limpeza/normalização e chaves de deduplicação
   - colunas derivadas (ex.: tech_stack, seniority, cidade/estado/país), enriquecimentos possíveis
   - expectativas/thresholds
C. Gerar notebooks DLT (PySpark) para cada domínio, implementando o plano.
D. Gerar as configs dos pipelines DLT (JSON) e comandos de criação/execução.
E. Executar pipeline, capturar métricas e devolver um RELATÓRIO estruturado.

Formato da sua resposta (obrigatório):
1) PLAN.yaml  — o plano de transformação proposto
2) NOTEBOOKS  — código DLT (PySpark) por domínio
3) PIPELINES  — arquivos JSON de configuração por domínio
4) RUN_STEPS  — comandos/steps para criar/atualizar/rodar os pipelines
5) REPORT.md  — resumo com métricas e próximos passos

Se encontrar ambiguidades, assuma padrões de mercado e explique sua decisão no PLAN.yaml. Sempre privilegie robustez, idempotência e governança UC.

```
---

## OBSERVAÇÕES

Plano de Transformação — Diretrizes (o que o agente deve inferir)
1) Bronze (padrão ingestão padronizada)
   - Leitura incremental/stream dos RAW.
   - Normalização mínima: trimming, lower/upper onde necessário, parse de datas, tipos.
   - Deduplicação por chave estável (ex.: job_url + posted_date), com watermark.
   - Expectations: job_title not null, company_name not null, posted_date parseável.

2) Silver (refino e normalização)
   - Padronização de location (split cidade/estado/país).
   - Extração de tecnologias de description_snippet (regex/dicionário).
   - Padronização de senioridade e regime (full-time/contract/hybrid).
   - Normalização de nomes de empresa.
   - Expectations mais rígidas; remoção de outliers.

3) Gold (métricas e insights)
   - gold_jobs_daily: contagem por dia, domínio, empresa, cidade, tech principal.
   - gold_top_techs: ranking de tecnologias (últimos 30/90 dias).
   - gold_trends: tendência semanal/mensal por domínio/região.
   - Views amigáveis para BI.

---
