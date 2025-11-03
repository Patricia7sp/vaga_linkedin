# Databricks notebook source
# MAGIC %md
# MAGIC # Verificar Datas de Extração

# COMMAND ----------

print("🔍 VERIFICANDO DATAS DE EXTRAÇÃO")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Últimas Extrações por Domain

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     domain,
# MAGIC     COUNT(*) as total_vagas,
# MAGIC     MIN(ingestion_timestamp) as primeira_ingestao,
# MAGIC     MAX(ingestion_timestamp) as ultima_ingestao,
# MAGIC     DATEDIFF(DAY, MAX(ingestion_timestamp), CURRENT_TIMESTAMP()) as dias_desde_ultima
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC GROUP BY domain
# MAGIC ORDER BY domain;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Vagas por Data de Ingestão (últimos 30 dias)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     DATE(ingestion_timestamp) as data_ingestao,
# MAGIC     COUNT(*) as total_vagas
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE ingestion_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
# MAGIC GROUP BY DATE(ingestion_timestamp)
# MAGIC ORDER BY data_ingestao DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Vagas Brasileiras vs Internacionais

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     CASE 
# MAGIC         WHEN LOWER(city) LIKE '%brazil%' OR LOWER(city) LIKE '%brasil%' 
# MAGIC              OR LOWER(city) LIKE '%paulo%' OR LOWER(city) LIKE '%rio%' 
# MAGIC         THEN 'Brasil'
# MAGIC         ELSE 'Internacional'
# MAGIC     END as origem,
# MAGIC     COUNT(*) as total
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC GROUP BY origem;

# COMMAND ----------

print("=" * 80)
print("✅ ANÁLISE COMPLETA!")
print("=" * 80)
print()
print("📊 CONCLUSÃO:")
print("   - Se última ingestão é antiga: precisa rodar Extract Agent")
print("   - Se todas são internacionais: Extract Agent está com geo_id errado")
