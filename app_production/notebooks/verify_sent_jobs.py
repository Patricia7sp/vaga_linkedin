# Databricks notebook source
# MAGIC %md
# MAGIC # Verificar Vagas Enviadas

# COMMAND ----------

print("📊 VERIFICANDO VAGAS ENVIADAS PELO AGENT CHAT")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Total de Vagas Enviadas

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     COUNT(*) as total_enviadas,
# MAGIC     MIN(notified_ts) as primeira_enviada,
# MAGIC     MAX(notified_ts) as ultima_enviada
# MAGIC FROM vagas_linkedin.viz.chat_agent_sent_jobs;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Últimas 10 Vagas Enviadas

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     job_id,
# MAGIC     notified_ts
# MAGIC FROM vagas_linkedin.viz.chat_agent_sent_jobs
# MAGIC ORDER BY notified_ts DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Checkpoint Atualizado

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     last_posted_time_ts,
# MAGIC     DATEDIFF(MINUTE, last_posted_time_ts, CURRENT_TIMESTAMP()) as minutos_atras
# MAGIC FROM vagas_linkedin.viz.chat_agent_state
# MAGIC ORDER BY last_posted_time_ts DESC
# MAGIC LIMIT 1;

# COMMAND ----------

print("=" * 80)
print("✅ VERIFICAÇÃO COMPLETA!")
print("=" * 80)
print()
print("📊 SE:")
print("   - total_enviadas > 0: ✅ Agent Chat funcionou!")
print("   - checkpoint atualizado: ✅ Próxima execução será incremental")
