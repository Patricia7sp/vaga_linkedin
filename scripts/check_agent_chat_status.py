#!/usr/bin/env python3
"""
Script para verificar status do Agent Chat no Databricks
"""

import os
import requests
import json
from datetime import datetime

# Configurações
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "https://dbc-14d16b60-2882.cloud.databricks.com")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "ab43ca87b28a5a1d")

if not DATABRICKS_TOKEN:
    raise RuntimeError("DATABRICKS_TOKEN não configurado")

headers = {
    "Authorization": f"Bearer {DATABRICKS_TOKEN}",
    "Content-Type": "application/json",
}

def execute_sql(query: str):
    """Executa query SQL via REST API."""
    url = f"{DATABRICKS_HOST}/api/2.0/sql/statements"
    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": query,
        "wait_timeout": "30s",
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    if response.status_code != 200:
        raise RuntimeError(f"Erro ao executar SQL: {response.status_code} - {response.text}")
    
    data = response.json()
    status = data.get("status", {}).get("state")
    
    if status == "FAILED":
        raise RuntimeError(f"Query falhou: {json.dumps(data, ensure_ascii=False)}")
    
    if status == "FINISHED":
        result = data.get("result")
        if not result:
            return []
        
        columns = [col["name"] for col in result.get("schema", {}).get("columns", [])]
        rows = result.get("data_array", [])
        
        return [dict(zip(columns, row)) for row in rows]
    
    return []

print("=" * 70)
print("📊 STATUS DO AGENT CHAT - DATABRICKS")
print("=" * 70)
print()

# 1. Checkpoint
print("🔖 CHECKPOINT ATUAL:")
try:
    checkpoint = execute_sql("""
        SELECT last_posted_time_ts 
        FROM vagas_linkedin.viz.chat_agent_state 
        ORDER BY last_posted_time_ts DESC 
        LIMIT 1
    """)
    if checkpoint:
        ts = checkpoint[0]["last_posted_time_ts"]
        print(f"   ✅ {ts}")
    else:
        print("   ⚠️  Nenhum checkpoint encontrado (primeira execução)")
except Exception as e:
    print(f"   ❌ Erro: {e}")

print()

# 2. Vagas Gold
print("📈 VAGAS NA VIEW GOLD:")
try:
    gold = execute_sql("""
        SELECT 
            COUNT(*) as total, 
            MAX(ingestion_timestamp) as ultima_ingestao,
            MAX(posted_time_ts) as ultima_postagem
        FROM vagas_linkedin.viz.vw_jobs_gold_all
    """)
    if gold:
        row = gold[0]
        print(f"   Total: {row['total']}")
        print(f"   Última ingestão: {row['ultima_ingestao']}")
        print(f"   Última postagem: {row['ultima_postagem']}")
except Exception as e:
    print(f"   ❌ Erro: {e}")

print()

# 3. Vagas Enviadas
print("📧 VAGAS JÁ ENVIADAS:")
try:
    sent = execute_sql("""
        SELECT 
            COUNT(*) as total,
            MAX(notified_ts) as ultima_notificacao
        FROM vagas_linkedin.viz.chat_agent_sent_jobs
    """)
    if sent:
        row = sent[0]
        print(f"   Total enviado: {row['total']}")
        print(f"   Última notificação: {row['ultima_notificacao']}")
    else:
        print("   ⚠️  Nenhuma vaga enviada ainda")
except Exception as e:
    print(f"   ❌ Erro: {e}")

print()

# 4. Vagas Novas Pendentes (simulando query do agent)
print("🆕 VAGAS NOVAS PENDENTES:")
try:
    # Pegar checkpoint
    checkpoint_result = execute_sql("""
        SELECT last_posted_time_ts 
        FROM vagas_linkedin.viz.chat_agent_state 
        ORDER BY last_posted_time_ts DESC 
        LIMIT 1
    """)
    
    if checkpoint_result:
        checkpoint_ts = checkpoint_result[0]["last_posted_time_ts"]
        
        # Buscar vagas novas (mesma query do agent com fix SQL)
        new_jobs = execute_sql(f"""
            SELECT
                job_id,
                title,
                company,
                COALESCE(posted_time_ts, ingestion_timestamp) as posted_time_ts
            FROM vagas_linkedin.viz.vw_jobs_gold_all
            WHERE ingestion_timestamp > TIMESTAMP '{checkpoint_ts}'
              AND job_id NOT IN (
                  SELECT job_id FROM vagas_linkedin.viz.chat_agent_sent_jobs
              )
            ORDER BY ingestion_timestamp ASC
            LIMIT 5
        """)
        
        if new_jobs:
            print(f"   ✅ {len(new_jobs)} vaga(s) nova(s) encontrada(s):")
            for job in new_jobs:
                print(f"      - [{job['job_id']}] {job['title']} ({job['company']})")
        else:
            print("   ℹ️  Nenhuma vaga nova desde último checkpoint")
    else:
        print("   ⚠️  Checkpoint não definido - não é possível verificar")
        
except Exception as e:
    print(f"   ❌ Erro: {e}")

print()
print("=" * 70)
print("✅ Verificação concluída!")
print("=" * 70)
