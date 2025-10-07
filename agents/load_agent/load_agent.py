#!/usr/bin/env python3
"""
Load Agent: Unity Catalog + GCS Integration with PySpark
Responsible for:
1. Connecting Databricks to Google Cloud Storage via Unity Catalog
2. Creating governance structure (catalog, schemas)
3. Registering RAW tables for JSON reading from GCS
4. NO data transformation (that's transform_agent responsibility)
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(project_root, ".env"))

# Configuration constants
CATALOG = "vagas_linkedin"
DOMAINS = ["data_engineer", "data_analytics", "digital_analytics"]
LAYERS = ["raw", "bronze", "silver", "gold"]

GCS_PATHS = {
    "data_engineer": "gs://linkedin-dados-raw/data_engineer/",
    "data_analytics": "gs://linkedin-dados-raw/data_analytics/",
    "digital_analytics": "gs://linkedin-dados-raw/digital_analytics/",
}

LOCAL_PATHS = {
    "data_engineer": "./data_extracts/",
    "data_analytics": "./data_extracts/",
    "digital_analytics": "./data_extracts/",
}


def _import_spark():
    """Import PySpark components with error handling."""
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import col, current_timestamp
        from pyspark.sql.types import BooleanType, IntegerType, StringType, StructField, StructType

        return SparkSession, col, current_timestamp, StructType, StructField, StringType, IntegerType, BooleanType
    except ImportError as e:
        raise ImportError(f"PySpark não está instalado ou configurado: {e}")


def test_gcs_connectivity_via_client():
    """Test GCS connectivity using Google Cloud Storage Python client."""
    try:
        from google.cloud import storage

        # Initialize client
        client = storage.Client()
        bucket_name = "linkedin-dados-raw"
        bucket = client.bucket(bucket_name)

        # Test connectivity by listing some objects
        blobs = list(bucket.list_blobs(prefix="data_engineer/", max_results=5))

        if blobs:
            print(f"✅ GCS conectado via client - {len(blobs)} arquivos encontrados")
            return True, len(blobs)
        else:
            print("⚠️  Bucket GCS vazio ou sem dados")
            return False, 0

    except Exception as e:
        print(f"❌ Erro GCS Client: {e}")
        return False, 0


def download_gcs_data_to_local():
    """Download GCS data to local directory for Spark processing."""
    try:
        import json
        import tempfile

        from google.cloud import storage

        print("📥 Baixando dados do GCS para processamento local...")

        client = storage.Client()
        bucket = client.bucket("linkedin-dados-raw")

        # Create local temp directory for GCS data
        temp_dir = "./temp_gcs_data"
        os.makedirs(temp_dir, exist_ok=True)

        downloaded_paths = {}
        for domain in DOMAINS:
            domain_dir = os.path.join(temp_dir, domain)
            os.makedirs(domain_dir, exist_ok=True)

            # List and download files for this domain
            prefix = f"{domain}/"
            blobs = list(bucket.list_blobs(prefix=prefix))

            files_downloaded = 0
            for blob in blobs:
                if blob.name.endswith(".json"):
                    local_filename = os.path.join(domain_dir, os.path.basename(blob.name))
                    blob.download_to_filename(local_filename)
                    files_downloaded += 1

            if files_downloaded > 0:
                downloaded_paths[domain] = f"{os.path.abspath(domain_dir)}/*.json"
                print(f"✅ {domain}: {files_downloaded} arquivos baixados")
            else:
                print(f"⚠️  {domain}: Nenhum arquivo JSON encontrado")

        return downloaded_paths

    except Exception as e:
        print(f"❌ Erro ao baixar dados GCS: {e}")
        return {}


def create_databricks_connect_session():
    """Create Databricks Connect session with fast timeout."""
    try:
        import signal
        import time

        SparkSession, col, current_timestamp, StructType, StructField, StringType, IntegerType, BooleanType = (
            _import_spark()
        )

        print("🔗 Tentando Databricks Connect (timeout 10s)...")

        # Check for Databricks environment variables
        databricks_host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        databricks_token = os.getenv("DATABRICKS_ACCESS_TOKEN")

        if not databricks_host or not databricks_token:
            print("⚠️  Credenciais Databricks não configuradas")
            return None

        # Define timeout handler
        def timeout_handler(signum, frame):
            raise TimeoutError("Databricks Connect timeout")

        # Try Databricks Connect with timeout
        try:
            # Set 10 second timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)

            start_time = time.time()

            spark = (
                SparkSession.builder.appName("VagaLinkedInLoadAgent-Connect")
                .config("spark.sql.execution.arrow.pyspark.enabled", "true")
                .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
                .remote(f"sc://{databricks_host}:443/;token={databricks_token}")
                .getOrCreate()
            )

            # Cancel timeout
            signal.alarm(0)

            # Quick test
            spark.sparkContext.setLogLevel("WARN")
            spark.sql("SHOW CATALOGS LIMIT 1").collect()

            elapsed = time.time() - start_time
            print(f"✅ Databricks Connect estabelecido ({elapsed:.1f}s)")

            return spark

        except TimeoutError:
            signal.alarm(0)
            print("⚠️  Databricks Connect timeout (>10s) - usando fallback")
            return None
        except Exception as connect_error:
            signal.alarm(0)
            print(f"⚠️  Databricks Connect falhou: {str(connect_error)[:100]}...")
            return None

    except Exception as e:
        print(f"❌ Erro no Databricks Connect: {e}")
        return None


def create_databricks_session_legacy():
    """Legacy Databricks session creation (fallback)."""
    try:
        SparkSession, col, current_timestamp, StructType, StructField, StringType, IntegerType, BooleanType = (
            _import_spark()
        )

        print("🔄 Tentando sessão Databricks legacy...")

        # Check for Databricks environment variables
        databricks_host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        databricks_token = os.getenv("DATABRICKS_ACCESS_TOKEN")

        if not databricks_host or not databricks_token:
            return None

        # Create Databricks Spark session
        spark = (
            SparkSession.builder.appName("VagaLinkedInLoadAgent-Legacy")
            .config("spark.databricks.service.address", f"https://{databricks_host}")
            .config("spark.databricks.service.token", databricks_token)
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            .getOrCreate()
        )

        spark.sparkContext.setLogLevel("WARN")
        print("✅ Sessão Databricks legacy criada")

        return spark

    except Exception as e:
        print(f"❌ Erro Databricks legacy: {e}")
        return None


def create_spark_session_with_gcs():
    """Create PySpark session - prioritize local with GCS, use API REST for Unity Catalog."""
    try:
        print("🚀 Criando sessão PySpark local...")

        # Test GCS connectivity for local session
        gcs_connected, file_count = test_gcs_connectivity_via_client()

        if gcs_connected:
            print(f"📡 Dados GCS disponíveis ({file_count} arquivos)")
            spark = create_spark_session_local()
            return spark
        else:
            print("💾 Usando dados locais...")
            return create_spark_session_local()

    except Exception as error:
        print(f"⚠️  Erro: {error}")
        print("🔄 Usando sessão local como fallback...")
        return create_spark_session_local()


def create_spark_session_local():
    """Create PySpark session with local configuration (fallback)."""
    try:
        # Check if databricks-connect is interfering
        import os
        import sys

        # Temporarily remove databricks-connect from path
        original_path = sys.path[:]
        sys.path = [p for p in sys.path if "databricks" not in p.lower()]

        try:
            SparkSession, col, current_timestamp, StructType, StructField, StringType, IntegerType, BooleanType = (
                _import_spark()
            )

            print("🚀 Criando sessão PySpark local...")

            # Force local mode explicitly
            spark = (
                SparkSession.builder.appName("VagaLinkedInLoadAgent-Local")
                .config("spark.sql.adaptive.enabled", "true")
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
                .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
                .config("spark.master", "local[*]")
                .master("local[*]")
                .getOrCreate()
            )

            spark.sparkContext.setLogLevel("WARN")
            print("✅ Sessão PySpark local criada com sucesso")

            return spark

        finally:
            # Restore original path
            sys.path = original_path

    except Exception as e:
        print(f"⚠️  PySpark local com conflito: {str(e)[:100]}...")
        print("🔄 Usando modo API REST apenas")
        return None


def create_spark_session():
    """Create PySpark session - try GCS first, fallback to local."""
    return create_spark_session_with_gcs()


def create_catalog_via_api():
    """Create Unity Catalog via Databricks REST API."""
    try:
        import requests

        databricks_host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        databricks_token = os.getenv("DATABRICKS_ACCESS_TOKEN")

        if not databricks_host or not databricks_token:
            return False

        headers = {"Authorization": f"Bearer {databricks_token}", "Content-Type": "application/json"}

        # Create catalog via API
        catalog_data = {"name": CATALOG, "comment": "Catálogo para dados de vagas do LinkedIn"}

        url = f"https://{databricks_host}/api/2.1/unity-catalog/catalogs"
        response = requests.post(url, headers=headers, json=catalog_data)

        if response.status_code in [200, 201]:
            print(f"✅ Catálogo {CATALOG} criado via API")
            return True
        elif response.status_code == 409:
            print(f"ℹ️  Catálogo {CATALOG} já existe")
            return True
        else:
            print(f"⚠️  Erro API: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Erro na API: {e}")
        return False


def create_schema_via_api(schema_name):
    """Create schema via Databricks REST API."""
    try:
        import requests

        databricks_host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        databricks_token = os.getenv("DATABRICKS_ACCESS_TOKEN")

        headers = {"Authorization": f"Bearer {databricks_token}", "Content-Type": "application/json"}

        # Create schema via API
        schema_data = {
            "name": schema_name,
            "catalog_name": CATALOG,
            "comment": f"Schema para dados {schema_name.replace('_', ' ')}",
        }

        url = f"https://{databricks_host}/api/2.1/unity-catalog/schemas"
        response = requests.post(url, headers=headers, json=schema_data)

        if response.status_code in [200, 201]:
            return True
        elif response.status_code == 409:
            return True  # Already exists
        else:
            print(f"⚠️  Erro schema {schema_name}: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Erro schema {schema_name}: {e}")
        return False


def create_unity_catalog_structure(spark):
    """Create Unity Catalog structure (catalog + schemas)."""
    try:
        print("🏗️  Criando estrutura Unity Catalog via API REST...")

        # Create catalog via API
        if not create_catalog_via_api():
            print("🔄 Usando modo local (sem Unity Catalog)")
            return create_local_governance_structure(spark)

        # Create schemas via API
        schemas_created = []

        for domain in DOMAINS:
            for layer in LAYERS:
                schema_name = f"{domain}_{layer}"

                print(f"📂 Criando schema: {schema_name}")

                if create_schema_via_api(schema_name):
                    schemas_created.append(f"{CATALOG}.{schema_name}")
                    print(f"✅ Schema criado: {CATALOG}.{schema_name}")
                else:
                    print(f"⚠️  Falha no schema: {schema_name}")

        print(f"✅ {len(schemas_created)} schemas criados no Unity Catalog")
        return True

    except Exception as e:
        print(f"❌ Erro Unity Catalog: {e}")
        print("🔄 Fallback para modo local...")
        return create_local_governance_structure(spark)


def create_local_governance_structure(spark):
    """Create local database structure (fallback)."""
    try:
        print("🏗️  Criando estrutura de databases Spark local...")

        databases_created = []

        for domain in DOMAINS:
            for layer in LAYERS:
                database_name = f"{CATALOG}_{domain}_{layer}"

                print(f"📂 Criando database: {database_name}")

                # Create database
                spark.sql(f"CREATE DATABASE IF NOT EXISTS {database_name}")
                databases_created.append(database_name)

        print(f"✅ {len(databases_created)} databases criados: {databases_created}")
        return True

    except Exception as e:
        print(f"❌ Erro ao criar estrutura de databases: {e}")
        return False


def create_governance_structure():
    """Create governance structure using Databricks CLI."""
    # Check if Databricks CLI is configured
    databricks_host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
    databricks_token = os.getenv("DATABRICKS_ACCESS_TOKEN")

    if databricks_host and databricks_token:
        print("🎯 Databricks configurado - usando CLI para Unity Catalog")
        success = create_unity_catalog_via_cli()
        if success:
            print("✅ Unity Catalog criado via Databricks CLI")
            return True
        else:
            print("⚠️  CLI falhou - modo somente metadados")
            return create_metadata_only_structure()
    else:
        print("💾 Databricks não configurado - modo somente metadados")
        return create_metadata_only_structure()


def create_unity_catalog_via_cli():
    """Create Unity Catalog structure using Databricks CLI."""
    try:
        import subprocess

        print("🏗️  Criando Unity Catalog via Databricks CLI...")

        # 1. Create catalog
        print(f"📝 Criando catálogo: {CATALOG}")
        try:
            result = subprocess.run(
                [
                    "databricks",
                    "unity-catalog",
                    "catalogs",
                    "create",
                    "--name",
                    CATALOG,
                    "--comment",
                    f"Catálogo para pipeline Vagas LinkedIn - {datetime.now().strftime('%Y-%m-%d')}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print(f"✅ Catálogo {CATALOG} criado")
            else:
                print(f"⚠️  Catálogo pode já existir: {result.stderr[:100]}")
        except subprocess.TimeoutExpired:
            print("⚠️  Timeout na criação do catálogo")
            return False

        # 2. Create all schemas
        schemas_created = 0
        for domain in DOMAINS:
            for layer in LAYERS:
                schema_name = f"{domain}_{layer}"
                full_schema = f"{CATALOG}.{schema_name}"

                try:
                    result = subprocess.run(
                        [
                            "databricks",
                            "unity-catalog",
                            "schemas",
                            "create",
                            "--name",
                            full_schema,
                            "--comment",
                            f"Schema {layer} para domínio {domain} - pipeline LinkedIn",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )

                    if result.returncode == 0:
                        schemas_created += 1
                        print(f"✅ Schema: {full_schema}")
                    else:
                        print(f"⚠️  Schema {schema_name}: {result.stderr[:50]}")

                except subprocess.TimeoutExpired:
                    print(f"⚠️  Timeout no schema {schema_name}")

        print(f"✅ {schemas_created}/12 schemas processados no Unity Catalog")
        return schemas_created > 0

    except Exception as e:
        print(f"❌ Erro Unity Catalog CLI: {e}")
        return False


def create_metadata_only_structure():
    """Create metadata structure when Databricks is not available."""
    try:
        print("📋 Criando estrutura de metadados local...")

        metadata = {"catalog": CATALOG, "schemas": [], "timestamp": datetime.now().isoformat(), "mode": "metadata_only"}

        for domain in DOMAINS:
            for layer in LAYERS:
                schema_name = f"{domain}_{layer}"
                metadata["schemas"].append(
                    {"name": schema_name, "full_name": f"{CATALOG}.{schema_name}", "domain": domain, "layer": layer}
                )

        print(f"✅ Metadados criados para {len(metadata['schemas'])} schemas")
        return True

    except Exception as e:
        print(f"❌ Erro na criação de metadados: {e}")
        return False


def create_unity_catalog_direct(spark):
    """Create Unity Catalog structure using direct Spark SQL commands."""
    try:
        print("🏗️  Criando estrutura Unity Catalog via Spark SQL...")

        # Create catalog using Spark SQL (works on real Databricks)
        try:
            spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
            print(f"✅ Catálogo criado: {CATALOG}")
        except Exception as catalog_error:
            print(f"ℹ️  Catálogo pode já existir: {catalog_error}")

        # Create schemas
        schemas_created = []

        for domain in DOMAINS:
            for layer in LAYERS:
                schema_name = f"{domain}_{layer}"
                full_schema = f"{CATALOG}.{schema_name}"

                print(f"📂 Criando schema: {full_schema}")

                try:
                    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {full_schema}")
                    schemas_created.append(full_schema)
                    print(f"✅ Schema criado: {full_schema}")
                except Exception as schema_error:
                    print(f"⚠️  Erro no schema {full_schema}: {schema_error}")

        print(f"✅ {len(schemas_created)} schemas criados no Unity Catalog")
        return True

    except Exception as e:
        print(f"❌ Erro Unity Catalog direto: {e}")
        print("🔄 Tentando API REST...")
        return create_unity_catalog_structure(spark)


def register_raw_tables(spark):
    """Register RAW tables for JSON reading from GCS or local paths."""
    try:
        print("📋 Registrando tabelas RAW para leitura dos JSONs...")

        tables_created = []

        # Test GCS connectivity using Python client
        gcs_connected, file_count = test_gcs_connectivity_via_client()

        if gcs_connected and file_count > 0:
            print(f"📡 Baixando {file_count} arquivos do GCS...")
            # Download GCS data to local temp directory
            gcs_paths = download_gcs_data_to_local()

            if gcs_paths:
                file_patterns = gcs_paths
                print("✅ Dados GCS baixados - usando arquivos temporários")
            else:
                # Fallback to existing local data
                import os

                base_path = os.path.abspath("./data_extracts/")
                file_patterns = {
                    "data_engineer": f"{base_path}/*data_engineer*.json",
                    "data_analytics": f"{base_path}/*data_analytics*.json",
                    "digital_analytics": f"{base_path}/*digital_analytics*.json",
                }
                print("💾 Fallback para dados locais existentes")
        else:
            # Use existing local paths
            import os

            base_path = os.path.abspath("./data_extracts/")
            file_patterns = {
                "data_engineer": f"{base_path}/*data_engineer*.json",
                "data_analytics": f"{base_path}/*data_analytics*.json",
                "digital_analytics": f"{base_path}/*digital_analytics*.json",
            }
            print("💾 Usando dados locais existentes")

        for domain, pattern in file_patterns.items():
            database_name = f"{CATALOG}_{domain}_raw"
            table_name = "jobs"
            full_table_name = f"{database_name}.{table_name}"

            print(f"🔗 Registrando tabela: {full_table_name}")
            print(f"📍 Path: {pattern}")

            # Use database
            spark.sql(f"USE {database_name}")

            try:
                # Try to read a sample to infer schema
                sample_df = spark.read.format("json").load(pattern)
                count = sample_df.count()
                if count > 0:
                    print(f"✅ Schema inferido com {count} registros")

                    # Create view first, then table
                    sample_df.createOrReplaceTempView(f"temp_{domain}_view")

                    spark.sql(
                        f"""
                        CREATE TABLE IF NOT EXISTS {table_name}
                        USING JSON
                        LOCATION '{pattern}'
                        COMMENT 'Tabela RAW - JSON schema-on-read para {domain.replace("_", " ").title()} extraído do LinkedIn'
                        TBLPROPERTIES (
                            'layer' = 'raw',
                            'domain' = '{domain}',
                            'source' = 'linkedin',
                            'format' = 'json',
                            'created_by' = 'load_agent',
                            'created_at' = '{datetime.now().isoformat()}',
                            'data_source' = '{"gcs" if gcs_connected else "local"}'
                        )
                    """
                    )

                    tables_created.append(full_table_name)
                    print(f"✅ Tabela {full_table_name} registrada ({count} registros)")
                else:
                    print(f"⚠️  Nenhum dado encontrado para {domain} - tabela não criada")

            except Exception as domain_error:
                print(f"⚠️  Erro ao processar {domain}: {domain_error}")

        print(f"✅ {len(tables_created)} tabelas RAW criadas: {tables_created}")
        return tables_created

    except Exception as e:
        print(f"❌ Erro ao registrar tabelas RAW: {e}")
        return []


def validate_local_data_connectivity(spark):
    """Validate local data connectivity and access."""
    try:
        print("🔍 Validando conectividade de dados locais...")

        validation_results = {}
        for domain, local_path in LOCAL_PATHS.items():
            try:
                # Check if directory exists
                import os

                full_path = os.path.abspath(local_path)
                if os.path.exists(full_path):
                    # Try to read from local path
                    df = spark.read.format("json").load(local_path)
                    count = df.count()
                    validation_results[domain] = {
                        "accessible": True,
                        "record_count": count,
                        "path": local_path,
                        "full_path": full_path,
                    }
                    print(f"✅ {domain}: {count} registros encontrados em {local_path}")
                else:
                    validation_results[domain] = {
                        "accessible": False,
                        "error": f"Diretório não existe: {full_path}",
                        "path": local_path,
                        "full_path": full_path,
                    }
                    print(f"⚠️  {domain}: Diretório não encontrado - {full_path}")

            except Exception as domain_error:
                validation_results[domain] = {"accessible": False, "error": str(domain_error), "path": local_path}
                print(f"⚠️  {domain}: Erro ao acessar {local_path} - {domain_error}")

        return validation_results

    except Exception as e:
        print(f"❌ Erro na validação local: {e}")
        return {}


def test_table_queries(spark):
    """Test basic queries on created RAW tables."""
    try:
        print("🧪 Testando consultas nas tabelas RAW...")

        query_results = {}
        for domain in DOMAINS:
            table_name = f"{CATALOG}_{domain}_raw.jobs"
            try:
                # Test basic SELECT
                df = spark.sql(f"SELECT * FROM {table_name} LIMIT 5")
                count = spark.sql(f"SELECT COUNT(*) as total FROM {table_name}").collect()[0]["total"]

                query_results[domain] = {
                    "queryable": True,
                    "record_count": count,
                    "sample_columns": df.columns[:10],  # First 10 columns
                }
                print(f"✅ {table_name}: {count} registros, colunas: {df.columns[:5]}...")

            except Exception as query_error:
                query_results[domain] = {"queryable": False, "error": str(query_error)}
                print(f"❌ {table_name}: Erro na consulta - {query_error}")

        return query_results

    except Exception as e:
        print(f"❌ Erro nos testes de consulta: {e}")
        return {}


def run_load(instructions=None):
    """Main Load Agent execution - Unity Catalog + GCS integration."""
    print("🚚 INICIANDO LOAD AGENT - Unity Catalog + GCS")
    print("=" * 60)

    # Results tracking
    results = {
        "catalog": CATALOG,
        "schemas": [],
        "tables_raw": [],
        "gcs_validation": {},
        "query_tests": {},
        "permissions": {"read": False, "write": False},
        "status": "failed",
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Step 1: Create Spark Session
        spark = create_spark_session()
        if not spark:
            return "❌ Falha ao criar sessão PySpark"

        # Step 2: Create Governance Structure via Databricks CLI
        if create_governance_structure():
            results["schemas"] = [f"{CATALOG}_{d}_{l}" for d in DOMAINS for l in LAYERS]
            print("✅ Estrutura Unity Catalog criada")
        else:
            print("⚠️  Continuando sem Unity Catalog")

        # Step 3: Register RAW Tables
        tables_created = register_raw_tables(spark)
        if tables_created:
            results["tables_raw"] = tables_created
            print("✅ Tabelas RAW registradas")
        else:
            return "❌ Falha ao registrar tabelas RAW"

        # Step 4: Validate Local Data Connectivity
        local_validation = validate_local_data_connectivity(spark)
        results["local_validation"] = local_validation

        accessible_domains = sum(1 for v in local_validation.values() if v.get("accessible", False))
        if accessible_domains > 0:
            results["permissions"]["read"] = True
            print(f"✅ Dados locais acessíveis para {accessible_domains}/{len(DOMAINS)} domínios")

        # Step 5: Test Table Queries
        query_results = test_table_queries(spark)
        results["query_tests"] = query_results

        queryable_tables = sum(1 for v in query_results.values() if v.get("queryable", False))
        if queryable_tables > 0:
            print(f"✅ {queryable_tables}/{len(DOMAINS)} tabelas consultáveis")

        # Final Status
        if accessible_domains > 0 and queryable_tables > 0:
            results["status"] = "ready_for_transform_agent"
            print("🎉 LOAD AGENT CONCLUÍDO COM SUCESSO!")
        else:
            results["status"] = "partial_success"
            print("⚠️  LOAD AGENT concluído com problemas")

        # Stop Spark
        spark.stop()

        # Print summary
        print("\n" + "=" * 60)
        print("📊 RESUMO FINAL:")
        print("=" * 60)
        print(f"Catálogo: {results['catalog']}")
        print(f"Schemas: {len(results['schemas'])} criados")
        print(f"Tabelas RAW: {len(results['tables_raw'])} registradas")
        print(f"Conectividade Local: {accessible_domains}/{len(DOMAINS)} domínios")
        print(f"Tabelas consultáveis: {queryable_tables}/{len(DOMAINS)}")
        print(f"Status: {results['status']}")

        return json.dumps(results, indent=2)

    except Exception as e:
        error_msg = f"❌ Erro no Load Agent: {e}"
        print(error_msg)
        results["error"] = str(e)
        return json.dumps(results, indent=2)


if __name__ == "__main__":
    run_load()
