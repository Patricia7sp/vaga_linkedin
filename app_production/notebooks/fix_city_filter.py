# Databricks notebook source
# MAGIC %md
# MAGIC # CORREÇÃO URGENTE - Filtro de Cidades

# COMMAND ----------

print("🔧 DIAGNÓSTICO E CORREÇÃO DO FILTRO DE CIDADES")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Ver Cidades REAIS na View (sem filtro)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     city,
# MAGIC     LOWER(city) as city_lower,
# MAGIC     COUNT(*) as total
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-01 00:00:00'
# MAGIC GROUP BY city, LOWER(city)
# MAGIC ORDER BY total DESC
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Verificar se Campo City Existe

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     COUNT(*) as total_vagas,
# MAGIC     COUNT(city) as total_com_city,
# MAGIC     COUNT(*) - COUNT(city) as total_sem_city
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-01 00:00:00';

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Primeiras 10 Vagas (SEM filtro de cidade)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     job_id,
# MAGIC     title,
# MAGIC     company,
# MAGIC     city,
# MAGIC     country,
# MAGIC     effective_posted_time
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-01 00:00:00'
# MAGIC ORDER BY effective_posted_time DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Testar com LIKE ao invés de IN

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     COUNT(*) as total_brasil
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-01 00:00:00'
# MAGIC   AND (
# MAGIC       LOWER(city) LIKE '%paulo%' OR
# MAGIC       LOWER(city) LIKE '%rio%' OR
# MAGIC       LOWER(city) LIKE '%belo%' OR
# MAGIC       LOWER(city) LIKE '%brasilia%' OR
# MAGIC       LOWER(city) LIKE '%curitiba%'
# MAGIC   );

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Verificar Country

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     country,
# MAGIC     COUNT(*) as total
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-01 00:00:00'
# MAGIC GROUP BY country
# MAGIC ORDER BY total DESC;

# COMMAND ----------

print("=" * 80)
print("✅ DIAGNÓSTICO COMPLETO!")
print("=" * 80)
print()
print("📊 ANÁLISE:")
print("   Célula 1: Mostra as cidades REAIS (com grafia exata)")
print("   Célula 2: Verifica se campo 'city' existe")
print("   Célula 3: Mostra vagas SEM filtro de cidade")
print("   Célula 4: Testa filtro com LIKE")
print("   Célula 5: Mostra países")
