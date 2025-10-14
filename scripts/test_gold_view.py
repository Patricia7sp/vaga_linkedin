#!/usr/bin/env python3
import os
import requests

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "https://dbc-14d16b60-2882.cloud.databricks.com")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "ab43ca87b28a5a1d")

headers = {
    "Authorization": f"Bearer {DATABRICKS_TOKEN}",
    "Content-Type": "application/json",
}

def execute_sql(query: str):
    url = f"{DATABRICKS_HOST}/api/2.0/sql/statements"
    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": query,
        "wait_timeout": "30s",
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    data = response.json()
    
    if data.get("status", {}).get("state") == "FINISHED":
        result = data.get("result")
        if result:
            columns = [col["name"] for col in result.get("schema", {}).get("columns", [])]
            rows = result.get("data_array", [])
            return [dict(zip(columns, row)) for row in rows]
    return []

print("🔍 Verificando view vw_jobs_gold_all...")

# Primeiro verificar se a view existe
try:
    tables = execute_sql("""
        SHOW VIEWS IN vagas_linkedin.viz
    """)
    print(f"📋 Views no schema viz: {len(tables)}")
    gold_view_exists = any('vw_jobs_gold_all' in str(t.values()) for t in tables)
    print(f"   vw_jobs_gold_all existe? {gold_view_exists}")
except Exception as e:
    print(f"   ⚠️  Erro ao listar views: {e}")

# Agora verificar dados
try:
    result = execute_sql("""
        SELECT COUNT(*) as total,
               MAX(ingestion_timestamp) as max_ingest,
               COUNT(DISTINCT domain) as num_domains
        FROM vagas_linkedin.viz.vw_jobs_gold_all
    """)
    if result:
        r = result[0]
        print(f"\n✅ View acessível!")
        print(f"   Total vagas: {r['total']}")
        print(f"   Última ingestão: {r['max_ingest']}")
        print(f"   Domínios: {r['num_domains']}")
        
        if r['total'] and r['total'] > 0:
            # Verificar amostra
            print("\n📋 Amostra de 3 vagas mais recentes:")
            sample = execute_sql("""
                SELECT domain, job_id, title, company, ingestion_timestamp
                FROM vagas_linkedin.viz.vw_jobs_gold_all
                ORDER BY ingestion_timestamp DESC
                LIMIT 3
            """)
            for job in sample:
                print(f"   - [{job['domain']}] {job['title']} | {job['company']}")
                print(f"     ID: {job['job_id']} | Ingestão: {job['ingestion_timestamp']}")
        else:
            print("\n⚠️  View existe mas está VAZIA")
    else:
        print("❌ View não retornou dados")
except Exception as e:
    print(f"❌ Erro ao acessar view: {e}")
