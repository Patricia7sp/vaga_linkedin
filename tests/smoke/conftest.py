"""
Configuração de fixtures para smoke tests.
"""

import os
import pytest


def pytest_configure(config):
    """Configura pytest para smoke tests."""
    config.addinivalue_line("markers", "smoke: smoke tests for post-deployment validation")


@pytest.fixture(scope="session")
def setup_gcp_env():
    """Setup de variáveis de ambiente GCP para smoke tests."""
    # Define valores padrão se não estiverem configurados
    env_defaults = {
        "GCP_PROJECT_ID": "vaga-linkedin",
        "GCP_REGION": "us-central1",
        "ENVIRONMENT": "staging",
    }

    for key, value in env_defaults.items():
        if key not in os.environ:
            os.environ[key] = value

    yield

    # Cleanup (se necessário)
    pass
