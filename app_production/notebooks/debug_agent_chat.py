# Databricks notebook source
# MAGIC %md
# MAGIC # Debug Agent Chat - Análise Detalhada
# MAGIC 
# MAGIC Verifica checkpoint, vagas disponíveis e vagas já enviadas

# COMMAND ----------

print("=" * 80)
print("🔍 DEBUG DO AGENT CHAT")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Verificar Checkpoint Atual

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     last_posted_time_ts,
# MAGIC     CURRENT_TIMESTAMP() as agora,
# MAGIC     DATEDIFF(DAY, last_posted_time_ts, CURRENT_TIMESTAMP()) as dias_atras,
# MAGIC     DATEDIFF(HOUR, last_posted_time_ts, CURRENT_TIMESTAMP()) as horas_atras
# MAGIC FROM vagas_linkedin.viz.chat_agent_state
# MAGIC ORDER BY last_posted_time_ts DESC
# MAGIC LIMIT 1;

# COMMAND ----------

print("📌 Se a tabela acima está vazia, o Agent Chat usará default de 30 dias")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Vagas Disponíveis na View (desde 16/10)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     COUNT(*) as total_vagas,
# MAGIC     MIN(effective_posted_time) as primeira_vaga,
# MAGIC     MAX(effective_posted_time) as ultima_vaga
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-16 00:00:00'
# MAGIC   AND LOWER(city) IN (
# MAGIC       'são paulo', 'rio de janeiro', 'belo horizonte', 'brasília', 'curitiba',
# MAGIC       'porto alegre', 'salvador', 'fortaleza', 'recife'
# MAGIC   );

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Vagas por Cidade (desde 16/10)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     LOWER(city) as cidade,
# MAGIC     COUNT(*) as total
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-16 00:00:00'
# MAGIC   AND LOWER(city) IN (
# MAGIC       'são paulo', 'rio de janeiro', 'belo horizonte', 'brasília', 'curitiba'
# MAGIC   )
# MAGIC GROUP BY LOWER(city)
# MAGIC ORDER BY total DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Vagas JÁ Enviadas

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     COUNT(*) as total_enviadas,
# MAGIC     MIN(notified_ts) as primeira_enviada,
# MAGIC     MAX(notified_ts) as ultima_enviada
# MAGIC FROM vagas_linkedin.viz.chat_agent_sent_jobs;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Vagas DISPONÍVEIS para Envio (últimos 30 dias)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     COUNT(*) as vagas_disponiveis
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time > CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
# MAGIC   AND job_id NOT IN (
# MAGIC       SELECT job_id FROM vagas_linkedin.viz.chat_agent_sent_jobs
# MAGIC   )
# MAGIC   AND LOWER(city) IN (
# MAGIC       'são paulo', 'rio de janeiro', 'belo horizonte', 'brasília', 'curitiba',
# MAGIC       'porto alegre', 'salvador', 'fortaleza', 'recife'
# MAGIC   );

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Primeiras 10 Vagas Disponíveis

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     job_id,
# MAGIC     title,
# MAGIC     company,
# MAGIC     city,
# MAGIC     effective_posted_time
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time > CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
# MAGIC   AND job_id NOT IN (
# MAGIC       SELECT job_id FROM vagas_linkedin.viz.chat_agent_sent_jobs
# MAGIC   )
# MAGIC   AND LOWER(city) IN (
# MAGIC       'são paulo', 'rio de janeiro', 'belo horizonte', 'brasília', 'curitiba'
# MAGIC   )
# MAGIC ORDER BY effective_posted_time ASC
# MAGIC LIMIT 10;

# COMMAND ----------

print("=" * 80)
print("✅ DEBUG COMPLETO!")
print("=" * 80)
