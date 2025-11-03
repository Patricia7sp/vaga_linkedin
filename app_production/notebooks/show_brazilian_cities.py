# Databricks notebook source
# MAGIC %md
# MAGIC # Mostrar Cidades das Vagas Brasileiras

# COMMAND ----------

print("🇧🇷 VAGAS BRASILEIRAS - CIDADES REAIS")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Cidades das 36 Vagas Brasileiras

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     city,
# MAGIC     LOWER(city) as city_lower,
# MAGIC     COUNT(*) as total
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE (
# MAGIC     LOWER(city) LIKE '%brazil%' OR LOWER(city) LIKE '%brasil%' 
# MAGIC     OR LOWER(city) LIKE '%paulo%' OR LOWER(city) LIKE '%rio%'
# MAGIC )
# MAGIC AND ingestion_timestamp > '2025-10-25'
# MAGIC GROUP BY city, LOWER(city)
# MAGIC ORDER BY total DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Todas as 36 Vagas Brasileiras

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     job_id,
# MAGIC     title,
# MAGIC     company,
# MAGIC     city,
# MAGIC     country,
# MAGIC     work_modality,
# MAGIC     effective_posted_time
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE (
# MAGIC     LOWER(city) LIKE '%brazil%' OR LOWER(city) LIKE '%brasil%' 
# MAGIC     OR LOWER(city) LIKE '%paulo%' OR LOWER(city) LIKE '%rio%'
# MAGIC )
# MAGIC AND ingestion_timestamp > '2025-10-25'
# MAGIC ORDER BY effective_posted_time DESC;

# COMMAND ----------

print("=" * 80)
print("✅ ANÁLISE COMPLETA!")
print("=" * 80)
print()
print("📊 Use essas cidades para atualizar o filtro do Agent Chat")
