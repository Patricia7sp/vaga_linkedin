"""
Pytest configuration and fixtures for Vagas LinkedIn tests
"""
import pytest
import sys
import os


@pytest.fixture(scope="session")
def project_root():
    """Get project root directory"""
    return os.path.dirname(os.path.dirname(__file__))


@pytest.fixture(scope="session")
def add_project_to_path(project_root):
    """Add project root to Python path"""
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    yield project_root
    # Cleanup not needed for path manipulation


@pytest.fixture
def sample_domains():
    """Sample domain names for testing"""
    return ["data_engineer", "data_analytics", "digital_analytics"]


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        "catalog": "vagas_linkedin",
        "environment": "test",
        "domains": ["data_engineer", "data_analytics", "digital_analytics"]
    }


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "databricks: mark test as requiring Databricks connection"
    )
