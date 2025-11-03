# Databricks notebook source
# MAGIC %md
# MAGIC # Agent Chat - SEM Filtro de Cidades (TESTE)
# MAGIC 
# MAGIC **TESTE URGENTE:** Remover filtro de cidades para verificar se vagas são enviadas

# COMMAND ----------

print("🚀 Agent Chat - TESTE SEM FILTRO DE CIDADES")
print("=" * 80)

# COMMAND ----------

import sys
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List
import requests

# COMMAND ----------

@dataclass
class JobRecord:
    job_id: str
    title: str
    company: str
    work_modality: str
    url: str
    posted_time_ts: datetime
    domain: str = "unknown"

# COMMAND ----------

STATE_TABLE = "vagas_linkedin.viz.chat_agent_state"
SENT_TABLE = "vagas_linkedin.viz.chat_agent_sent_jobs"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Limpar Checkpoint

# COMMAND ----------

spark.sql(f"DELETE FROM {STATE_TABLE}")
print("✅ Checkpoint limpo!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Buscar Vagas (SEM filtro de cidades)

# COMMAND ----------

since = datetime.now() - timedelta(days=30)
since_literal = f"TIMESTAMP '{since.strftime('%Y-%m-%d %H:%M:%S')}'"

# Query SEM filtro de cidades
query = f"""
SELECT
    domain,
    job_id,
    title,
    company,
    work_modality,
    city,
    url,
    effective_posted_time as posted_time_ts
FROM vagas_linkedin.viz.vw_jobs_gold_all
WHERE effective_posted_time > {since_literal}
  AND job_id NOT IN (
      SELECT job_id FROM {SENT_TABLE}
  )
ORDER BY effective_posted_time ASC
LIMIT 10
"""

print(f"🔍 Buscando vagas desde: {since}")
print(f"📊 Query SEM filtro de cidades")
print()

df = spark.sql(query)
rows = df.collect()

print(f"✅ Vagas encontradas: {len(rows)}")
print()

if rows:
    print("📋 Primeiras vagas:")
    for i, row in enumerate(rows[:5], 1):
        print(f"   {i}. {row['title'][:40]}... | {row['company'][:25]} | {row['city']}")
else:
    print("⚠️  Nenhuma vaga encontrada!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Resultado

# COMMAND ----------

if len(rows) > 0:
    print("=" * 80)
    print(f"🎉 SUCESSO! {len(rows)} VAGAS ENCONTRADAS SEM FILTRO DE CIDADES!")
    print("=" * 80)
    print()
    print("📊 CONCLUSÃO:")
    print("   ✅ View tem dados")
    print("   ✅ Query funciona sem filtro")
    print("   ❌ PROBLEMA: Filtro de cidades está bloqueando tudo")
    print()
    print("🔧 SOLUÇÃO:")
    print("   1. Verificar grafia real das cidades no notebook fix_city_filter")
    print("   2. Ajustar filtro no Agent Chat")
    print("   3. Ou remover filtro temporariamente")
else:
    print("=" * 80)
    print("❌ PROBLEMA: Nenhuma vaga encontrada mesmo SEM filtro!")
    print("=" * 80)
    print()
    print("📊 POSSÍVEIS CAUSAS:")
    print("   - Campo effective_posted_time não existe")
    print("   - View está vazia")
    print("   - Todas as vagas já foram enviadas")
