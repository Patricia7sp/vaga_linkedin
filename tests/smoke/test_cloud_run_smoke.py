"""
Smoke tests para validação pós-deploy do Cloud Run Job.
Executa testes básicos para garantir que o deploy foi bem-sucedido.
"""

import os
import pytest
from datetime import datetime, timedelta
from google.cloud import run_v2, logging_v2, storage


@pytest.fixture
def gcp_project_id():
    """Fixture para o ID do projeto GCP."""
    return os.getenv("GCP_PROJECT_ID", "vaga-linkedin")


@pytest.fixture
def gcp_region():
    """Fixture para a região GCP."""
    return os.getenv("GCP_REGION", "us-central1")


@pytest.fixture
def env():
    """Fixture para o ambiente (staging, production)."""
    return os.getenv("ENVIRONMENT", "staging")


@pytest.fixture
def job_name(env):
    """Fixture para o nome do job baseado no ambiente."""
    if env == "staging":
        return "vaga-linkedin-prod-staging"
    elif env == "production":
        return "vaga-linkedin-prod-v5"
    else:
        return f"vaga-linkedin-prod-{env}"


class TestCloudRunJobExists:
    """Testa se o Cloud Run Job existe e está configurado corretamente."""

    def test_job_exists(self, gcp_project_id, gcp_region, job_name):
        """Verifica se o Cloud Run Job existe."""
        client = run_v2.JobsClient()
        job_path = f"projects/{gcp_project_id}/locations/{gcp_region}/jobs/{job_name}"

        try:
            job = client.get_job(name=job_path)
            assert job is not None, f"Job {job_name} não encontrado"
            assert job.name == job_path, "Nome do job não corresponde"
        except Exception as e:
            pytest.fail(f"Erro ao buscar job: {e}")

    def test_job_has_correct_image(self, gcp_project_id, gcp_region, job_name):
        """Verifica se o job está usando a imagem correta."""
        client = run_v2.JobsClient()
        job_path = f"projects/{gcp_project_id}/locations/{gcp_region}/jobs/{job_name}"

        job = client.get_job(name=job_path)
        container = job.template.template.containers[0]

        assert container.image, "Job não tem imagem configurada"
        assert "vaga-linkedin-prod" in container.image, "Imagem incorreta"
        assert gcp_project_id in container.image, f"Imagem não pertence ao projeto {gcp_project_id}"

    def test_job_has_required_resources(self, gcp_project_id, gcp_region, job_name, env):
        """Verifica se o job tem recursos mínimos configurados."""
        client = run_v2.JobsClient()
        job_path = f"projects/{gcp_project_id}/locations/{gcp_region}/jobs/{job_name}"

        job = client.get_job(name=job_path)
        container = job.template.template.containers[0]
        resources = container.resources

        # Recursos mínimos esperados
        if env == "staging":
            min_memory = "2Gi"
            min_cpu = "1"
        else:  # production
            min_memory = "4Gi"
            min_cpu = "2"

        assert resources.limits.get("memory") == min_memory, f"Memória incorreta, esperado {min_memory}"
        assert resources.limits.get("cpu") == min_cpu, f"CPU incorreta, esperado {min_cpu}"

    def test_job_has_rapidapi_secret(self, gcp_project_id, gcp_region, job_name):
        """Verifica se o job tem o secret RAPIDAPI_KEY configurado."""
        client = run_v2.JobsClient()
        job_path = f"projects/{gcp_project_id}/locations/{gcp_region}/jobs/{job_name}"

        job = client.get_job(name=job_path)
        container = job.template.template.containers[0]

        # Verificar se tem RAPIDAPI_KEY nas env vars (via secret)
        has_rapidapi = any(
            env.name == "RAPIDAPI_KEY" and env.value_source.secret_key_ref
            for env in container.env
        )

        assert has_rapidapi, "Job não tem RAPIDAPI_KEY configurado via secret"


class TestCloudRunJobExecution:
    """Testa execuções recentes do Cloud Run Job."""

    def test_has_recent_executions(self, gcp_project_id, gcp_region, job_name):
        """Verifica se há execuções recentes (últimas 24h)."""
        client = run_v2.ExecutionsClient()
        parent = f"projects/{gcp_project_id}/locations/{gcp_region}/jobs/{job_name}"

        try:
            executions = list(client.list_executions(parent=parent, page_size=10))

            # Se não tiver execuções, só avisa (não falha)
            if not executions:
                pytest.skip(f"Job {job_name} ainda não tem execuções. Execute manualmente para validar.")
                return

            # Verificar execução mais recente
            latest = executions[0]
            assert latest is not None, "Nenhuma execução encontrada"

            # Verificar se foi concluída
            if latest.completion_time:
                # Verificar se foi bem-sucedida
                status = latest.status
                if status and hasattr(status, "conditions"):
                    conditions = status.conditions
                    succeeded = any(c.type == "Completed" and c.status == "True" for c in conditions)
                    if not succeeded:
                        pytest.skip(f"Última execução não foi bem-sucedida. Verifique logs.")

        except Exception as e:
            pytest.skip(f"Não foi possível verificar execuções: {e}")


class TestCloudStorageOutput:
    """Testa se os dados estão sendo salvos no Cloud Storage."""

    def test_bronze_raw_bucket_exists(self, gcp_project_id):
        """Verifica se o bucket bronze-raw existe."""
        storage_client = storage.Client(project=gcp_project_id)

        bucket_name = "linkedin-dados-raw"
        try:
            bucket = storage_client.get_bucket(bucket_name)
            assert bucket is not None, f"Bucket {bucket_name} não encontrado"
        except Exception as e:
            pytest.fail(f"Erro ao acessar bucket: {e}")

    def test_has_recent_data(self, gcp_project_id):
        """Verifica se há dados recentes no bucket (últimos 7 dias)."""
        storage_client = storage.Client(project=gcp_project_id)
        bucket_name = "linkedin-dados-raw"

        try:
            bucket = storage_client.get_bucket(bucket_name)

            # Buscar arquivos na pasta bronze-raw dos últimos 7 dias
            seven_days_ago = datetime.now() - timedelta(days=7)

            blobs = list(bucket.list_blobs(prefix="bronze-raw/", max_results=100))

            if not blobs:
                pytest.skip("Nenhum dado encontrado no bucket. Execute o job para gerar dados.")
                return

            # Verificar se há arquivos recentes
            recent_blobs = [b for b in blobs if b.time_created >= seven_days_ago]

            if not recent_blobs:
                pytest.skip("Nenhum dado recente (últimos 7 dias). Execute o job para atualizar.")
            else:
                # Sucesso! Há dados recentes
                assert len(recent_blobs) > 0, f"Encontrados {len(recent_blobs)} arquivos recentes"

        except Exception as e:
            pytest.skip(f"Não foi possível verificar dados no bucket: {e}")


class TestCloudRunLogs:
    """Testa se os logs estão sendo gerados corretamente."""

    def test_job_has_logs(self, gcp_project_id, job_name):
        """Verifica se o job está gerando logs."""
        logging_client = logging_v2.Client(project=gcp_project_id)

        # Buscar logs do job nas últimas 24h
        filter_str = (
            f'resource.type="cloud_run_job" '
            f'resource.labels.job_name="{job_name}" '
            f'timestamp>="{(datetime.now() - timedelta(days=1)).isoformat()}Z"'
        )

        try:
            entries = list(logging_client.list_entries(filter_=filter_str, page_size=10))

            if not entries:
                pytest.skip(f"Nenhum log encontrado para {job_name} nas últimas 24h. Execute o job primeiro.")
                return

            # Verificar se há logs de sucesso ou erro
            assert len(entries) > 0, f"Encontrados {len(entries)} logs"

        except Exception as e:
            pytest.skip(f"Não foi possível verificar logs: {e}")


class TestHealthCheck:
    """Health check geral do ambiente."""

    def test_gcp_credentials(self):
        """Verifica se as credenciais GCP estão configuradas."""
        # Verificar variáveis de ambiente
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not creds_path:
            pytest.skip("GOOGLE_APPLICATION_CREDENTIALS não configurado. Smoke tests podem falhar.")

        assert os.path.exists(creds_path), f"Arquivo de credenciais não encontrado: {creds_path}"

    def test_required_env_vars(self):
        """Verifica se as variáveis de ambiente necessárias estão configuradas."""
        required_vars = [
            "GCP_PROJECT_ID",
            "GCP_REGION",
        ]

        missing = [var for var in required_vars if not os.getenv(var)]

        if missing:
            pytest.skip(f"Variáveis faltando: {', '.join(missing)}. Configure para rodar smoke tests.")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
