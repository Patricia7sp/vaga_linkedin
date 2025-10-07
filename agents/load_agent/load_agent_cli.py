#!/usr/bin/env python3
"""
Load Agent - Unity Catalog via CLI puro (sem PySpark)
Versão otimizada usando apenas Databricks CLI e JSON direto
"""
import glob
import json
import os
import subprocess
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CATALOG = "vagas_linkedin"
DOMAINS = ["data_analytics", "data_engineer", "digital_analytics"]
LAYERS = ["raw", "bronze", "silver", "gold"]

LOCAL_PATHS = {
    "data_analytics": "temp_gcs_data/data_analytics/*.json",
    "data_engineer": "temp_gcs_data/data_engineer/*.json",
    "digital_analytics": "temp_gcs_data/digital_analytics/*.json",
}


def test_gcs_connectivity():
    """Test GCS connectivity and file availability."""
    try:
        from google.cloud import storage

        bucket_name = os.getenv("GCP_BUCKET_NAME")
        if not bucket_name:
            return False, 0, []

        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # List blobs with pattern
        blobs = list(bucket.list_blobs(prefix="data_extracts/"))
        json_files = [blob.name for blob in blobs if blob.name.endswith(".json")]

        return True, len(json_files), json_files[:10]  # Return first 10 for display

    except Exception as e:
        return False, 0, []


def download_gcs_data():
    """Download GCS data to local temp directory."""
    try:
        from google.cloud import storage

        bucket_name = os.getenv("GCP_BUCKET_NAME")
        if not bucket_name:
            return {}

        client = storage.Client()
        bucket = client.bucket(bucket_name)

        downloaded_paths = {}

        for domain in DOMAINS:
            temp_dir = f"temp_gcs_data/{domain}"
            os.makedirs(temp_dir, exist_ok=True)

            # Download JSON files for this domain
            pattern = f"data_extracts/*/{domain}/*.json"
            blobs = bucket.list_blobs(prefix=f"data_extracts/")
            domain_blobs = [b for b in blobs if domain in b.name and b.name.endswith(".json")]

            local_files = []
            for blob in domain_blobs:
                local_path = f"{temp_dir}/{os.path.basename(blob.name)}"
                blob.download_to_filename(local_path)
                local_files.append(local_path)

            if local_files:
                downloaded_paths[domain] = local_files
                print(f"📁 {domain}: {len(local_files)} arquivos baixados")

        return downloaded_paths

    except Exception as e:
        print(f"⚠️  Erro GCS download: {e}")
        return {}


def create_storage_credentials():
    """Create GCS storage credentials in Databricks."""
    try:
        import json

        # Read GCS credentials
        with open("gcp-credentials.json", "r") as f:
            gcs_creds = json.load(f)

        storage_cred_name = "gcs_linkedin_creds"

        print(f"📝 Criando storage credentials: {storage_cred_name}")
        print(f"📧 Service account: {gcs_creds['client_email']}")

        # Create storage credential with GCS service account key
        result = subprocess.run(
            [
                "databricks",
                "unity-catalog",
                "storage-credentials",
                "create",
                "--name",
                storage_cred_name,
                "--gcp-sak-email",
                gcs_creds["client_email"],
                "--gcp-sak-private-key-id",
                gcs_creds["private_key_id"],
                "--gcp-sak-private-key",
                gcs_creds["private_key"],
                "--comment",
                "GCS credentials para vagas LinkedIn pipeline",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print(f"✅ Storage credentials criado")
            return storage_cred_name
        elif "already exists" in result.stderr.lower():
            print(f"✅ Storage credentials já existe")
            return storage_cred_name
        else:
            print(f"⚠️  Erro storage credentials: {result.stderr[:100]}")
            return None

    except Exception as e:
        print(f"⚠️  Erro storage credentials: {e}")
        return None


def create_external_location(storage_cred_name):
    """Create external location for GCS bucket."""
    try:
        gcs_uri = os.getenv("URI_gsutil", "gs://linkedin-dados-raw")
        external_location_name = "gcs_linkedin_location"

        print(f"📝 Criando external location: {external_location_name}")
        print(f"🗄️  GCS URI: {gcs_uri}")

        result = subprocess.run(
            [
                "databricks",
                "unity-catalog",
                "external-locations",
                "create",
                "--name",
                external_location_name,
                "--url",
                gcs_uri,
                "--storage-credential-name",
                storage_cred_name,
                "--comment",
                "External location para bucket GCS do pipeline LinkedIn",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print(f"✅ External location criado")
            return external_location_name
        elif "already exists" in result.stderr.lower():
            print(f"✅ External location já existe")
            return external_location_name
        else:
            print(f"⚠️  Erro external location: {result.stderr[:100]}")
            return None

    except Exception as e:
        print(f"⚠️  Erro external location: {e}")
        return None


def create_catalog_with_external_location(catalog_name, external_location_name):
    """Create catalog with external location via CLI."""
    try:
        print(f"📝 Criando catálogo: {catalog_name}")

        result = subprocess.run(
            [
                "databricks",
                "unity-catalog",
                "catalogs",
                "create",
                "--name",
                catalog_name,
                "--comment",
                f"Catálogo vagas LinkedIn com external location - {datetime.now().strftime('%Y-%m-%d')}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print(f"✅ Catálogo {catalog_name} criado")
            return True
        elif "already exists" in result.stderr.lower():
            print(f"✅ Catálogo {catalog_name} já existe")
            return True
        else:
            print(f"⚠️  Erro catálogo: {result.stderr[:100]}")
            return False

    except Exception as e:
        print(f"⚠️  Erro criar catálogo: {e}")
        return False


def create_unity_catalog_via_cli():
    """Create Unity Catalog structure using Databricks CLI."""
    try:
        print("🏗️  Criando Unity Catalog via Databricks CLI...")

        # Skip catalog creation - already exists manually
        print(f"✅ Usando catálogo existente: {CATALOG}")

        # Verify catalog exists
        try:
            result = subprocess.run(
                ["databricks", "unity-catalog", "catalogs", "get", "--name", CATALOG],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                print(f"✅ Catálogo {CATALOG} confirmado")
            else:
                print(f"⚠️  Catálogo {CATALOG} não encontrado - verifique se foi criado manualmente")
                return False
        except Exception as e:
            print(f"⚠️  Erro ao verificar catálogo: {e}")
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
                            "--catalog-name",
                            CATALOG,
                            "--name",
                            schema_name,
                            "--comment",
                            f"Schema {layer} para domínio {domain}",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )

                    if result.returncode == 0:
                        schemas_created += 1
                        print(f"✅ Schema: {full_schema}")
                    else:
                        if "already exists" in result.stderr.lower():
                            schemas_created += 1
                            print(f"✅ Schema {schema_name} já existe")
                        else:
                            print(f"⚠️  {schema_name}: {result.stderr[:50]}")

                except subprocess.TimeoutExpired:
                    print(f"⚠️  Timeout no schema {schema_name}")

        print(f"✅ {schemas_created}/12 schemas processados no Unity Catalog")
        return schemas_created > 0

    except Exception as e:
        print(f"❌ Erro Unity Catalog CLI: {e}")
        return False


def validate_local_data():
    """Validate local JSON data files."""
    try:
        print("🔍 Validando dados locais...")

        validation_results = {}
        total_records = 0

        for domain in DOMAINS:
            pattern = LOCAL_PATHS[domain]
            files = glob.glob(pattern)

            domain_records = 0
            valid_files = []

            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            domain_records += len(data)
                        else:
                            domain_records += 1
                        valid_files.append(file_path)
                except Exception as file_error:
                    print(f"⚠️  Erro em {file_path}: {file_error}")

            validation_results[domain] = {
                "files_found": len(files),
                "valid_files": len(valid_files),
                "records": domain_records,
                "accessible": len(valid_files) > 0,
            }

            total_records += domain_records
            print(f"📊 {domain}: {domain_records} registros em {len(valid_files)} arquivos")

        print(f"📈 Total: {total_records} registros em {len(DOMAINS)} domínios")
        return validation_results, total_records

    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        return {}, 0


def create_volumes_via_cli():
    """Create volumes in Unity Catalog via new Databricks CLI v0.267.0."""
    try:
        print("📁 Criando volumes no Unity Catalog via CLI v0.267.0...")

        gcs_uri = os.getenv("URI_gsutil", "gs://linkedin-dados-raw")
        volumes_created = []

        for domain in DOMAINS:
            schema_name = f"{domain}_raw"
            volume_name = "linkedin_data_volume"

            # GCS location for this domain (production path)
            gcs_location = f"{gcs_uri}/{domain}/"

            print(f"📁 Criando volume: {CATALOG}.{schema_name}.{volume_name}")
            print(f"🔗 GCS: {gcs_location}")

            # Create volume via CLI
            cmd = [
                "databricks",
                "volumes",
                "create",
                CATALOG,
                schema_name,
                volume_name,
                "EXTERNAL",
                "--storage-location",
                gcs_location,
                "--comment",
                f"Volume para dados JSON {domain.replace('_', ' ').title()} do LinkedIn no GCS",
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    volumes_created.append(f"{CATALOG}.{schema_name}.{volume_name}")
                    print(f"✅ Volume {CATALOG}.{schema_name}.{volume_name} criado via CLI")
                else:
                    print(f"⚠️  Erro ao criar volume: {result.stderr}")

            except subprocess.TimeoutExpired:
                print(f"⚠️  Timeout ao criar volume {CATALOG}.{schema_name}.{volume_name}")
            except Exception as e:
                print(f"⚠️  Erro CLI: {e}")

        print(f"✅ {len(volumes_created)}/3 volumes criados via CLI")
        return volumes_created

    except Exception as e:
        print(f"❌ Erro ao criar volumes via CLI: {e}")
        return []


def create_tables_referencing_volumes():
    """Create RAW tables that reference existing volumes."""
    try:
        print("📝 Criando tabelas RAW que referenciam volumes...")

        tables_created = []

        for domain in DOMAINS:
            schema_name = f"{domain}_raw"
            table_name = f"jobs_{domain}"
            full_table_name = f"{CATALOG}.{schema_name}.{table_name}"

            # Volume path for this domain
            volume_path = f"/Volumes/{CATALOG}/{schema_name}/linkedin_data_volume/*.json"

            print(f"📝 Criando tabela: {full_table_name}")
            print(f"📁 Volume: {volume_path}")

            create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {full_table_name}
USING JSON
OPTIONS (
  path '{volume_path}',
  multiline 'true'
)
COMMENT 'Tabela RAW para dados {domain.replace("_", " ").title()} extraídos do LinkedIn via volume'
TBLPROPERTIES (
  'layer' = 'raw',
  'domain' = '{domain}',
  'source' = 'linkedin',
  'format' = 'json',
  'created_by' = 'load_agent_cli',
  'created_at' = '{datetime.now().isoformat()}',
  'volume_path' = '/Volumes/{CATALOG}/{schema_name}/linkedin_data_volume/'
)
"""

            # Execute table creation
            table_success = execute_sql_command(create_table_sql.strip())

            if table_success:
                tables_created.append(full_table_name)
                print(f"✅ Tabela {full_table_name} criada")
            else:
                print(f"⚠️  Erro ao criar tabela {full_table_name}")

        return tables_created

    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return []


def create_volumes_and_tables_via_sql():
    """Create volumes and RAW tables in Unity Catalog via SQL commands."""
    try:
        print("🏗️  Criando volumes e tabelas RAW no Unity Catalog via SQL...")

        gcs_uri = os.getenv("URI_gsutil", "gs://linkedin-dados-raw")
        volumes_created = []
        tables_created = []

        for domain in DOMAINS:
            schema_name = f"{domain}_raw"
            volume_name = "linkedin_data_volume"
            table_name = f"jobs_{domain}"

            full_volume_name = f"{CATALOG}.{schema_name}.{volume_name}"
            full_table_name = f"{CATALOG}.{schema_name}.{table_name}"

            # GCS location for this domain (production path)
            gcs_location = f"{gcs_uri}/{domain}/"
            volume_path = f"/Volumes/{CATALOG}/{schema_name}/{volume_name}/*.json"

            print(f"📁 Criando volume: {full_volume_name}")
            print(f"🔗 GCS: {gcs_location}")

            # Create Volume SQL
            create_volume_sql = f"""
CREATE VOLUME IF NOT EXISTS {full_volume_name}
USING '{gcs_location}'
COMMENT 'Volume para dados JSON {domain.replace("_", " ").title()} do LinkedIn no GCS'
"""

            # Execute volume creation
            volume_success = execute_sql_command(create_volume_sql.strip())

            if volume_success:
                volumes_created.append(full_volume_name)
                print(f"✅ Volume {full_volume_name} criado")

                # Now create table referencing the volume
                print(f"📝 Criando tabela: {full_table_name}")

                create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {full_table_name}
USING JSON
OPTIONS (
  path '{volume_path}',
  multiline 'true'
)
COMMENT 'Tabela RAW para dados {domain.replace("_", " ").title()} extraídos do LinkedIn via volume'
TBLPROPERTIES (
  'layer' = 'raw',
  'domain' = '{domain}',
  'source' = 'linkedin',
  'format' = 'json',
  'created_by' = 'load_agent_cli',
  'created_at' = '{datetime.now().isoformat()}',
  'volume_path' = '/Volumes/{CATALOG}/{schema_name}/{volume_name}/',
  'gcs_location' = '{gcs_location}'
)
"""

                # Execute table creation
                table_success = execute_sql_command(create_table_sql.strip())

                if table_success:
                    tables_created.append(full_table_name)
                    print(f"✅ Tabela {full_table_name} criada")
                else:
                    print(f"⚠️  Erro ao criar tabela {full_table_name}")
            else:
                print(f"⚠️  Erro ao criar volume {full_volume_name}")

        print(f"✅ {len(volumes_created)}/3 volumes criados no Unity Catalog")
        print(f"✅ {len(tables_created)}/3 tabelas RAW criadas no Unity Catalog")

        return {
            "volumes_created": volumes_created,
            "tables_created": tables_created,
            "total_success": len(volumes_created) + len(tables_created),
        }

    except Exception as e:
        print(f"❌ Erro ao criar volumes e tabelas: {e}")
        return {"volumes_created": [], "tables_created": [], "total_success": 0}


def execute_sql_command(sql_command):
    """Execute SQL command via Databricks SQL API."""
    try:
        import requests

        databricks_host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        databricks_token = os.getenv("DATABRICKS_ACCESS_TOKEN")

        if not databricks_host or not databricks_token:
            print("⚠️  Credenciais Databricks não disponíveis")
            return False

        # Use SQL execution endpoint
        url = f"https://{databricks_host}/api/2.0/sql/statements"
        headers = {"Authorization": f"Bearer {databricks_token}", "Content-Type": "application/json"}

        # Get warehouse ID (simplified - using first available)
        warehouses_url = f"https://{databricks_host}/api/2.0/sql/warehouses"
        warehouses_response = requests.get(warehouses_url, headers=headers, timeout=30)

        if warehouses_response.status_code != 200:
            print("⚠️  Não foi possível obter SQL warehouse")
            return False

        warehouses = warehouses_response.json().get("warehouses", [])
        if not warehouses:
            print("⚠️  Nenhum SQL warehouse disponível")
            return False

        warehouse_id = warehouses[0]["id"]

        # Execute SQL
        data = {"warehouse_id": warehouse_id, "statement": sql_command, "wait_timeout": "30s"}

        response = requests.post(url, headers=headers, json=data, timeout=60)

        if response.status_code in [200, 201]:
            result = response.json()
            if result.get("status", {}).get("state") == "SUCCEEDED":
                return True
            else:
                print(f"⚠️  SQL falhou: {result.get('status', {}).get('error', 'Erro desconhecido')}")
                return False
        else:
            print(f"⚠️  Erro HTTP: {response.status_code}")
            return False

    except Exception as e:
        print(f"⚠️  Erro na execução SQL: {e}")
        return False


def create_table_metadata():
    """Create table metadata for Unity Catalog tables."""
    try:
        print("📋 Criando metadados das tabelas...")

        table_metadata = {}

        for domain in DOMAINS:
            table_name = f"{CATALOG}.{domain}_raw.jobs_{domain}"

            metadata = {
                "catalog": CATALOG,
                "schema": f"{domain}_raw",
                "table": f"jobs_{domain}",
                "full_name": table_name,
                "type": "EXTERNAL",
                "format": "JSON",
                "comment": f"Tabela RAW para dados {domain.replace('_', ' ').title()} do LinkedIn",
                "properties": {
                    "layer": "raw",
                    "domain": domain,
                    "source": "linkedin",
                    "format": "json",
                    "created_by": "load_agent_cli",
                    "created_at": datetime.now().isoformat(),
                },
            }

            table_metadata[domain] = metadata
            print(f"📝 Metadados: {table_name}")

        return table_metadata

    except Exception as e:
        print(f"❌ Erro nos metadados: {e}")
        return {}


def run_load_agent_cli(instructions=None):
    """Run Load Agent using CLI only (no PySpark)."""
    print("🚚 LOAD AGENT CLI - Unity Catalog + Dados JSON")
    print("=" * 60)

    results = {
        "catalog": CATALOG,
        "schemas_created": 0,
        "tables_metadata": {},
        "data_validation": {},
        "gcs_status": False,
        "total_records": 0,
        "status": "failed",
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Step 1: Test GCS connectivity
        gcs_connected, file_count, sample_files = test_gcs_connectivity()
        results["gcs_status"] = gcs_connected

        if gcs_connected:
            print(f"✅ GCS conectado - {file_count} arquivos disponíveis")
            print(f"📂 Exemplos: {sample_files[:3]}")

            # Download GCS data
            gcs_data = download_gcs_data()
        else:
            print("💾 Usando dados locais apenas")
            gcs_data = {}

        # Step 2: Create Unity Catalog via CLI
        databricks_host = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        databricks_token = os.getenv("DATABRICKS_ACCESS_TOKEN")

        if databricks_host and databricks_token:
            catalog_success = create_unity_catalog_via_cli()
            if catalog_success:
                results["schemas_created"] = 12
                print("✅ Unity Catalog criado via CLI")
            else:
                print("⚠️  Unity Catalog falhou - continuando")
        else:
            print("💾 Databricks não configurado")

        # Step 3: Validate local data
        data_validation, total_records = validate_local_data()
        results["data_validation"] = data_validation
        results["total_records"] = total_records

        # Step 4: Create volumes via CLI and tables via SQL
        print("\n" + "=" * 60)
        print("🏗️  ETAPA 4: CRIANDO VOLUMES E TABELAS RAW")
        print("=" * 60)

        # Try CLI volume creation first
        volumes_created = create_volumes_via_cli()
        results["volumes_created"] = volumes_created

        if volumes_created:
            print(f"✅ {len(volumes_created)} volumes criados via CLI")

            # Create tables that reference the volumes
            tables_created = create_tables_referencing_volumes()
            results["tables_created"] = tables_created

            if tables_created:
                print(f"✅ {len(tables_created)} tabelas RAW criadas via SQL")

                # Step 5: Create table metadata
                print("\n📋 Criando metadados...")
                table_metadata = create_table_metadata()
                results["table_metadata"] = table_metadata

                results["status"] = "ready_for_transform_agent"
                results["summary"] = (
                    f"Unity Catalog: {results['schemas_created']} schemas, {len(volumes_created)} volumes, {len(tables_created)} tabelas RAW, {total_records} registros"
                )
            else:
                print("⚠️  Tabelas não criadas - usando fallback metadata")
                table_metadata = create_table_metadata()
                results["table_metadata"] = table_metadata
                results["status"] = "volumes_only"
                results["summary"] = (
                    f"Unity Catalog: {results['schemas_created']} schemas, {len(volumes_created)} volumes, metadados apenas, {total_records} registros"
                )
        else:
            print("⚠️  Volumes não criados via CLI - tentando fallback SQL")
            # Fallback to SQL creation
            creation_results = create_volumes_and_tables_via_sql()
            results["volumes_created"] = creation_results["volumes_created"]
            results["tables_created"] = creation_results["tables_created"]

            if creation_results["total_success"] > 0:
                print(
                    f"✅ Fallback: {len(creation_results['volumes_created'])} volumes + {len(creation_results['tables_created'])} tabelas via SQL"
                )
                table_metadata = create_table_metadata()
                results["table_metadata"] = table_metadata
                results["status"] = "ready_for_transform_agent"
                results["summary"] = (
                    f"Unity Catalog: {results['schemas_created']} schemas, {len(creation_results['volumes_created'])} volumes, {len(creation_results['tables_created'])} tabelas RAW, {total_records} registros"
                )
            else:
                print("⚠️  Erro em volumes e tabelas - usando fallback metadata")
            table_metadata = create_table_metadata()
            results["table_metadata"] = table_metadata
            results["status"] = "metadata_only"
            results["summary"] = (
                f"Unity Catalog: {results['schemas_created']} schemas, metadados apenas, {total_records} registros"
            )

        # Print summary
        print("\n" + "=" * 60)
        print("📊 RESUMO FINAL:")
        print("=" * 60)
        print(f"Catálogo: {results['catalog']}")
        print(f"Schemas Unity Catalog: {results['schemas_created']}")
        print(f"GCS conectado: {results['gcs_status']}")
        print(f"Total de registros: {results['total_records']}")
        print(f"Domínios com dados: {len([d for d in data_validation.values() if d.get('accessible')])}/{len(DOMAINS)}")
        print(f"Status: {results['status']}")

        return json.dumps(results, indent=2)

    except Exception as e:
        error_msg = f"❌ Erro no Load Agent CLI: {e}"
        print(error_msg)
        results["error"] = str(e)
        return json.dumps(results, indent=2)


def run_load(instructions=None):
    """Compatibility function for control_agent integration."""
    return run_load_agent_cli(instructions)


if __name__ == "__main__":
    run_load_agent_cli()
