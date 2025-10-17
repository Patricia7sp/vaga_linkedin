# 🚚 Etapa 3 — LoadAgent (Unity Catalog + ligação ao GCS, sem transformação)

O `load_agent` é responsável por:

1. **Conectar** o Databricks ao Google Cloud Storage (GCS) via Unity Catalog.
2. Criar o **catálogo único** `vagas_linkedin`.
3. Criar **schemas combinando domínio + camada** (ex.: `data_engineer_raw`, `data_engineer_bronze`, etc.).
4. **Registrar tabelas RAW** apenas para leitura dos JSONs no GCS.
5. Garantir **governança** com Unity Catalog (RBAC, lineage, comentários, tags).
6. **Não** realizar transformação ou conversão de formato (isso é papel do `transform_agent`).

---

## 🧱 Estrutura de Governança

**Catálogo:** `vagas_linkedin`  

**Schemas (por domínio + camada):**
- `data_engineer_raw`, `data_engineer_bronze`, `data_engineer_silver`, `data_engineer_gold`
- `data_analytics_raw`, `data_analytics_bronze`, `data_analytics_silver`, `data_analytics_gold`
- `digital_analytics_raw`, `digital_analytics_bronze`, `digital_analytics_silver`, `digital_analytics_gold`

**Tabelas criadas nesta etapa (RAW):**
- `vagas_linkedin.data_engineer_raw.jobs` → `gs://linkedin-dados-raw/data_engineer/`
- `vagas_linkedin.data_analytics_raw.jobs` → `gs://linkedin-dados-raw/data_analytics/`
- `vagas_linkedin.digital_analytics_raw.jobs` → `gs://linkedin-dados-raw/digital_analytics/`

---

## 🔐 Credenciais e Permissões do GCS

- O Databricks acessa o GCS por meio de **Storage Credentials** no Unity Catalog.  
- **Permissões necessárias:**
  - **Leitura**: suficiente para consumir dados RAW.
  - **Escrita**: recomendada, pois camadas **bronze/silver/gold** podem precisar gravar dados de volta ao GCS ou em Volumes externos.  
  - Ideal: conceder ao Service Account **Storage Object Admin** para granularidade completa (leitura, escrita, deleção).
- **Validação:** antes de rodar o agente, confirme se:
  - A Service Account está associada corretamente ao credential no UC.
  - O Databricks consegue listar e ler objetos do bucket.
  - Há permissão para **escrita**, caso queira persistir dados transformados em GCS (mesmo que hoje só lemos RAW).

---

## 📘 Boas Práticas (Unity Catalog + Storage)

1. **Nomenclatura consistente**: use `snake_case` para catálogos, schemas e tabelas.
2. **Comentários/documentação**: adicione `COMMENT` em catálogo, schemas e tabelas para facilitar lineage.
3. **Tags/classificações**: utilize tags UC (ex.: `layer=raw`, `domain=data_engineer`, `source=linkedin`).
4. **RBAC**:
   - conceda apenas `SELECT` em RAW para a maioria dos usuários.
   - dê permissões de escrita apenas a times de engenharia responsáveis por ETL.
5. **Volumetria**: como os arquivos JSON podem crescer, considere usar **Volumes** ou Delta Tables (futuro no `transform_agent`).
6. **Particionamento**: se o `extract_agent` particiona por data, use isso nos filtros para otimizar consultas.
7. **Lineage**: Unity Catalog gera lineage automaticamente; aproveite para rastrear do RAW até GOLD.

---

## 📄 Exemplo PySpark Notebook

```python
# Configurações
CATALOG = "vagas_linkedin"
DOMAINS = ["data_engineer", "data_analytics", "digital_analytics"]
LAYERS  = ["raw", "bronze", "silver", "gold"]

GCS_PATHS = {
    "data_engineer":     "gs://linkedin-dados-raw/data_engineer/",
    "data_analytics":    "gs://linkedin-dados-raw/data_analytics/",
    "digital_analytics": "gs://linkedin-dados-raw/digital_analytics/"
}

# Criar catálogo
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG} COMMENT 'Catálogo governado para vagas LinkedIn';")
spark.sql(f"USE CATALOG {CATALOG}")

# Criar schemas
for d in DOMAINS:
    for l in LAYERS:
        schema = f"{d}_{l}"
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {schema} COMMENT '{l.upper()} — domínio {d}';")

# Criar tabelas RAW (schema-on-read, JSON)
for d, path in GCS_PATHS.items():
    schema = f"{d}_raw"
    spark.sql(f"USE SCHEMA {schema}")
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS jobs
        USING JSON
        LOCATION '{path}'
        COMMENT 'JSON bruto (schema-on-read) — {d.replace("_"," ").title()}';
    """)
```


## Checklist de Validação
- Storage Credential criado e com permissão de leitura (mínimo) e preferencialmente escrita.
- Catálogo vagas_linkedin criado.
- Schemas *_raw, *_bronze, *_silver, *_gold criados para cada domínio.
- Tabelas RAW criadas e acessíveis via SELECT.
- Logs de execução confirmam acesso ao GCS.

```json
{
  "catalog": "vagas_linkedin",
  "schemas": [
    "data_engineer_raw", "data_engineer_bronze", "data_engineer_silver", "data_engineer_gold",
    "data_analytics_raw", "data_analytics_bronze", "data_analytics_silver", "data_analytics_gold",
    "digital_analytics_raw", "digital_analytics_bronze", "digital_analytics_silver", "digital_analytics_gold"
  ],
  "tables_raw": [
    "vagas_linkedin.data_engineer_raw.jobs",
    "vagas_linkedin.data_analytics_raw.jobs",
    "vagas_linkedin.digital_analytics_raw.jobs"
  ],
  "permissions": {
    "read": true,
    "writ
    e": true
  },
  "status": "ready_for_transform_agent"
}

```