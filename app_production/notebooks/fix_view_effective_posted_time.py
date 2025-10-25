# Databricks notebook source
# MAGIC %md
# MAGIC # Correção da View vw_jobs_gold_all
# MAGIC 
# MAGIC **PROBLEMA:** View não identificava vagas novas desde 04/10/2025
# MAGIC 
# MAGIC **CAUSA:** Campo `posted_time_ts` pode ser NULL quando LinkedIn não fornece data
# MAGIC 
# MAGIC **SOLUÇÃO:** Adicionar campo `effective_posted_time` com COALESCE

# COMMAND ----------

print("🔧 Atualizando VIEW vw_jobs_gold_all...")
print("=" * 80)

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE VIEW vagas_linkedin.viz.vw_jobs_gold_all AS
# MAGIC SELECT 
# MAGIC     'data_engineer' AS domain,
# MAGIC     job_id,
# MAGIC     title,
# MAGIC     company,
# MAGIC     city,
# MAGIC     state,
# MAGIC     country,
# MAGIC     location_tier,
# MAGIC     category,
# MAGIC     search_term,
# MAGIC     work_modality,
# MAGIC     contract_type,
# MAGIC     salary_min,
# MAGIC     salary_max,
# MAGIC     salary_range,
# MAGIC     has_salary_info,
# MAGIC     is_premium_salary,
# MAGIC     posted_time_ts,
# MAGIC     is_recent_posting,
# MAGIC     description_quality_score,
# MAGIC     url,
# MAGIC     ingestion_timestamp,
# MAGIC     COALESCE(posted_time_ts, ingestion_timestamp) as effective_posted_time
# MAGIC FROM vagas_linkedin.data_engineer_dlt.data_engineer_gold
# MAGIC 
# MAGIC UNION ALL
# MAGIC 
# MAGIC SELECT 
# MAGIC     'data_analytics' AS domain,
# MAGIC     job_id,
# MAGIC     title,
# MAGIC     company,
# MAGIC     city,
# MAGIC     state,
# MAGIC     country,
# MAGIC     location_tier,
# MAGIC     category,
# MAGIC     search_term,
# MAGIC     work_modality,
# MAGIC     contract_type,
# MAGIC     salary_min,
# MAGIC     salary_max,
# MAGIC     salary_range,
# MAGIC     has_salary_info,
# MAGIC     is_premium_salary,
# MAGIC     posted_time_ts,
# MAGIC     is_recent_posting,
# MAGIC     description_quality_score,
# MAGIC     url,
# MAGIC     ingestion_timestamp,
# MAGIC     COALESCE(posted_time_ts, ingestion_timestamp) as effective_posted_time
# MAGIC FROM vagas_linkedin.data_analytics_dlt.data_analytics_gold
# MAGIC 
# MAGIC UNION ALL
# MAGIC 
# MAGIC SELECT 
# MAGIC     'digital_analytics' AS domain,
# MAGIC     job_id,
# MAGIC     title,
# MAGIC     company,
# MAGIC     city,
# MAGIC     state,
# MAGIC     country,
# MAGIC     location_tier,
# MAGIC     category,
# MAGIC     search_term,
# MAGIC     work_modality,
# MAGIC     contract_type,
# MAGIC     salary_min,
# MAGIC     salary_max,
# MAGIC     salary_range,
# MAGIC     has_salary_info,
# MAGIC     is_premium_salary,
# MAGIC     posted_time_ts,
# MAGIC     is_recent_posting,
# MAGIC     description_quality_score,
# MAGIC     url,
# MAGIC     ingestion_timestamp,
# MAGIC     COALESCE(posted_time_ts, ingestion_timestamp) as effective_posted_time
# MAGIC FROM vagas_linkedin.digital_analytics_dlt.digital_analytics_gold;

# COMMAND ----------

print("✅ View atualizada com sucesso!")
print()
print("📊 Verificando dados...")

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     domain,
# MAGIC     COUNT(*) as total_vagas,
# MAGIC     COUNT(posted_time_ts) as com_posted_time,
# MAGIC     COUNT(*) - COUNT(posted_time_ts) as sem_posted_time,
# MAGIC     MAX(effective_posted_time) as max_effective_time,
# MAGIC     MAX(ingestion_timestamp) as max_ingestion
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC GROUP BY domain
# MAGIC ORDER BY domain;

# COMMAND ----------

print("=" * 80)
print("✅ CORREÇÃO APLICADA COM SUCESSO!")
print("=" * 80)
print()
print("📌 PRÓXIMOS PASSOS:")
print("   1. Executar Agent Chat novamente")
print("   2. Verificar se vagas novas são identificadas")
print("   3. Confirmar envio para Telegram")
