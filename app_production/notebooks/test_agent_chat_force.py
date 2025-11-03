# Databricks notebook source
# MAGIC %md
# MAGIC # Teste Agent Chat - Forçar Busca desde 01/10

# COMMAND ----------

print("🔍 TESTE FORÇADO DO AGENT CHAT")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Limpar Checkpoint

# COMMAND ----------

# MAGIC %sql
# MAGIC DELETE FROM vagas_linkedin.viz.chat_agent_state;

# COMMAND ----------

print("✅ Checkpoint limpo!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Testar Query Diretamente (desde 01/10)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     COUNT(*) as total_vagas,
# MAGIC     MIN(effective_posted_time) as primeira,
# MAGIC     MAX(effective_posted_time) as ultima
# MAGIC FROM vagas_linkedin.viz.vw_jobs_gold_all
# MAGIC WHERE effective_posted_time >= TIMESTAMP '2025-10-01 00:00:00'
# MAGIC   AND LOWER(city) IN (
# MAGIC       'são paulo', 'rio de janeiro', 'belo horizonte', 'brasília', 'curitiba'
# MAGIC   );

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Verificar se Tabela sent_jobs Está Vazia

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT COUNT(*) as total_enviadas
# MAGIC FROM vagas_linkedin.viz.chat_agent_sent_jobs;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Buscar Vagas Disponíveis (NOT IN sent_jobs)

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 
# MAGIC     COUNT(*) as vagas_disponiveis
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
# MAGIC ## 5. Primeiras 10 Vagas Disponíveis

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
# MAGIC LIMIT 10;

# COMMAND ----------

print("=" * 80)
print("✅ TESTE COMPLETO!")
print("=" * 80)
print()
print("📊 ANÁLISE:")
print("   - Se 'total_vagas' > 0 e 'vagas_disponiveis' > 0:")
print("     ✅ Há vagas para enviar!")
print()
print("   - Se 'total_vagas' > 0 mas 'vagas_disponiveis' = 0:")
print("     ⚠️  Todas as vagas já foram enviadas")
print()
print("   - Se 'total_vagas' = 0:")
print("     ⚠️  Problema no filtro de cidades ou view")
