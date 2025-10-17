#!/usr/bin/env python3
"""
Script para diagnosticar por que Silver-MD não está processando dados novos
Compara dados entre Bronze, Silver-STG e Silver-MD
"""

from databricks.sdk import WorkspaceClient
import os

# Conectar ao Databricks
w = WorkspaceClient(
    host=os.getenv("DATABRICKS_HOST", "https://dbc-14d16b60-2882.cloud.databricks.com"),
    token=os.getenv("DATABRICKS_TOKEN")
)

warehouse_id = "ab43ca87b28a5a1d"

queries = {
    "1. Última data por camada": """
        SELECT 'Bronze' as layer, MAX(extract_date) as last_date, COUNT(*) as total_rows
        FROM vagas_linkedin.data_engineer_dlt.data_engineer_bronze
        UNION ALL
        SELECT 'Silver-STG', MAX(extract_date), COUNT(*)
        FROM vagas_linkedin.data_engineer_dlt.data_engineer_silver_stg
        UNION ALL
        SELECT 'Silver-MD', MAX(extract_date), COUNT(*)
        FROM vagas_linkedin.data_engineer_dlt.data_engineer_silver_md
        UNION ALL
        SELECT 'Gold', MAX(extract_date), COUNT(*)
        FROM vagas_linkedin.data_engineer_dlt.data_engineer_gold
        ORDER BY layer
    """,
    
    "2. Dados novos em STG mas não em MD": """
        SELECT 
            stg.extract_date,
            COUNT(DISTINCT stg.job_id) as jobs_in_stg,
            COUNT(DISTINCT md.job_id) as jobs_in_md,
            COUNT(DISTINCT stg.job_id) - COUNT(DISTINCT md.job_id) as difference
        FROM vagas_linkedin.data_engineer_dlt.data_engineer_silver_stg stg
        LEFT JOIN vagas_linkedin.data_engineer_dlt.data_engineer_silver_md md 
            ON stg.job_id = md.job_id AND stg.extract_date = md.extract_date
        WHERE stg.extract_date >= '2025-10-06'
        GROUP BY stg.extract_date
        ORDER BY stg.extract_date DESC
    """,
    
    "3. Job IDs únicos por camada (últimos 10 dias)": """
        SELECT 
            'Bronze' as layer,
            COUNT(DISTINCT job_id) as unique_jobs
        FROM vagas_linkedin.data_engineer_dlt.data_engineer_bronze
        WHERE extract_date >= '2025-10-06'
        UNION ALL
        SELECT 'Silver-STG', COUNT(DISTINCT job_id)
        FROM vagas_linkedin.data_engineer_dlt.data_engineer_silver_stg
        WHERE extract_date >= '2025-10-06'
        UNION ALL
        SELECT 'Silver-MD', COUNT(DISTINCT job_id)
        FROM vagas_linkedin.data_engineer_dlt.data_engineer_silver_md
        WHERE extract_date >= '2025-10-06'
        UNION ALL
        SELECT 'Gold', COUNT(DISTINCT job_id)
        FROM vagas_linkedin.data_engineer_dlt.data_engineer_gold
    """,
    
    "4. Verificar jobs descartados por expectations": """
        SELECT 
            COUNT(*) as total_rows,
            COUNT(CASE WHEN location IS NULL THEN 1 END) as null_location,
            COUNT(CASE WHEN length(location) <= 2 THEN 1 END) as short_location,
            COUNT(CASE WHEN job_id IS NULL THEN 1 END) as null_job_id
        FROM vagas_linkedin.data_engineer_dlt.data_engineer_silver_stg
        WHERE extract_date >= '2025-10-06'
    """
}

print("\n" + "="*80)
print("🔍 DIAGNÓSTICO: Por que Silver-MD não processa dados novos?")
print("="*80 + "\n")

for title, query in queries.items():
    print(f"\n{title}")
    print("-" * 60)
    
    try:
        result = w.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query,
            wait_timeout="30s"
        )
        
        if result.result and result.result.data_array:
            for row in result.result.data_array:
                print("  ", " | ".join(str(cell) for cell in row))
        else:
            print("   ℹ️  Sem resultados")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")

print("\n" + "="*80)
print("✅ Diagnóstico completo")
print("="*80 + "\n")
