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

print("=" * 70)
print("📊 AUDITORIA DATABRICKS - Schemas e Tabelas")
print("=" * 70)

# 1. Listar schemas
print("\n📁 SCHEMAS disponíveis:")
try:
    schemas = execute_sql("SHOW SCHEMAS IN vagas_linkedin")
    for schema in schemas:
        schema_name = schema.get('databaseName') or schema.get('namespace')
        print(f"   - {schema_name}")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 2. Schema viz
print("\n📋 Schema VIZ:")
try:
    viz_tables = execute_sql("SHOW TABLES IN vagas_linkedin.viz")
    if viz_tables:
        print(f"   ✅ {len(viz_tables)} objeto(s) encontrado(s):")
        for table in viz_tables:
            name = table.get('tableName')
            is_temp = table.get('isTemporary', False)
            print(f"      - {name} {'[TEMP]' if is_temp else ''}")
    else:
        print("   ⚠️  Schema viz existe mas está VAZIO")
except Exception as e:
    print(f"   ❌ Schema viz não existe ou erro: {e}")

# 3. Verificar schemas DLT (gold layers)
print("\n🏅 TABELAS GOLD (schemas DLT):")
for domain in ['data_engineer_dlt', 'data_analytics_dlt', 'digital_analytics_dlt']:
    try:
        tables = execute_sql(f"SHOW TABLES IN vagas_linkedin.{domain}")
        gold_tables = [t for t in tables if 'gold' in str(t.get('tableName', '')).lower()]
        if gold_tables:
            print(f"   ✅ {domain}: {len(gold_tables)} tabela(s) gold")
            for t in gold_tables:
                table_name = t.get('tableName')
                # Verificar contagem
                count_result = execute_sql(f"SELECT COUNT(*) as total FROM vagas_linkedin.{domain}.{table_name}")
                count = count_result[0]['total'] if count_result else 0
                print(f"      - {table_name}: {count} registros")
        else:
            print(f"   ⚠️  {domain}: Nenhuma tabela gold")
    except Exception as e:
        print(f"   ❌ {domain}: Schema não existe ou erro")

print("\n" + "=" * 70)
print("✅ Auditoria concluída!")
print("=" * 70)
