# Databricks notebook source
# MAGIC %md
# MAGIC # Resultados do Teste Agent Chat

# COMMAND ----------

print("=" * 80)
print("📊 RESULTADOS DO DIAGNÓSTICO")
print("=" * 80)
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Total de Vagas Disponíveis (desde 01/10)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     COUNT(*) as total_vagas,
# MAGIC     MIN(effective_posted_time) as primeira_vaga,
# MAGIC     MAX(effective_posted_time) as ultima_vaga
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-01 00:00:00'
# MAGIC   AND LOWER(city) IN (
# MAGIC       'são paulo', 'rio de janeiro', 'belo horizonte', 'brasília', 'curitiba'
# MAGIC   );

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Vagas Já Enviadas

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT COUNT(*) as total_enviadas
# MAGIC FROM vagas_linkedin.viz.chat_agent_sent_jobs;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Vagas DISPONÍVEIS para Envio

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     COUNT(*) as vagas_disponiveis_para_envio
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-01 00:00:00'
# MAGIC   AND job_id NOT IN (
# MAGIC       SELECT job_id FROM vagas_linkedin.viz.chat_agent_sent_jobs
# MAGIC   )
# MAGIC   AND LOWER(city) IN (
# MAGIC       'são paulo', 'rio de janeiro', 'belo horizonte', 'brasília', 'curitiba'
# MAGIC   );

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Checkpoint Atual

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     last_posted_time_ts,
# MAGIC     DATEDIFF(DAY, last_posted_time_ts, CURRENT_TIMESTAMP()) as dias_atras
# MAGIC FROM vagas_linkedin.viz.chat_agent_state
# MAGIC ORDER BY last_posted_time_ts DESC
# MAGIC LIMIT 1;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Primeiras 5 Vagas Disponíveis

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     job_id,
# MAGIC     title,
# MAGIC     company,
# MAGIC     city,
# MAGIC     effective_posted_time
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-01 00:00:00'
# MAGIC   AND job_id NOT IN (
# MAGIC       SELECT job_id FROM vagas_linkedin.viz.chat_agent_sent_jobs
# MAGIC   )
# MAGIC   AND LOWER(city) IN (
# MAGIC       'são paulo', 'rio de janeiro', 'belo horizonte'
# MAGIC   )
# MAGIC ORDER BY effective_posted_time ASC
# MAGIC LIMIT 5;

# COMMAND ----------

print("=" * 80)
print("✅ ANÁLISE COMPLETA!")
print("=" * 80)
