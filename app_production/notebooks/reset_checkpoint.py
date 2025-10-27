# Databricks notebook source
# MAGIC %md
# MAGIC # Reset Checkpoint do Agent Chat
# MAGIC 
# MAGIC Este notebook reseta o checkpoint para forçar busca de vagas dos últimos 30 dias

# COMMAND ----------

print("🔄 Resetando checkpoint do Agent Chat...")

# COMMAND ----------

# MAGIC %sql
# MAGIC DELETE FROM vagas_linkedin.viz.chat_agent_state;

# COMMAND ----------

print("✅ Checkpoint resetado!")
print("   Na próxima execução do Agent Chat, buscará vagas dos últimos 30 dias")
