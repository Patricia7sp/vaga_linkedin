"""
Basic unit tests for Vagas LinkedIn project
"""
import pytest


def test_imports():
    """Test that basic imports work"""
    import sys
    import os
    
    assert sys.version_info >= (3, 8), "Python 3.8+ required"
    assert os.path.exists("app_production"), "app_production directory should exist"


def test_python_version():
    """Test Python version compatibility"""
    import sys
    
    assert sys.version_info.major == 3
    assert sys.version_info.minor >= 8


def test_project_structure():
    """Test basic project structure"""
    import os
    
    required_dirs = [
        "app_production",
        "agents",
        "terraform",
        ".github"
    ]
    
    for dir_name in required_dirs:
        assert os.path.exists(dir_name), f"Directory {dir_name} should exist"


def test_configuration_files():
    """Test that configuration files exist"""
    import os
    
    config_files = [
        ".flake8",
        ".bandit",
        "pytest.ini",
        "requirements.txt"
    ]
    
    for file_name in config_files:
        assert os.path.exists(file_name), f"Config file {file_name} should exist"


class TestAgentStructure:
    """Test agent modules structure"""
    
    def test_agent_directories(self):
        """Test that agent directories exist"""
        import os
        
        agent_dirs = [
            "agents/extract_agent",
            "agents/load_agent",
            "agents/control_agent"
        ]
        
        for dir_name in agent_dirs:
            assert os.path.exists(dir_name), f"Agent directory {dir_name} should exist"
    
    def test_production_agents(self):
        """Test that production agent directories exist"""
        import os
        
        prod_agent_dirs = [
            "app_production/agents/extract_agent",
            "app_production/agents/transform_agent",
            "app_production/agents/control_agent"
        ]
        
        for dir_name in prod_agent_dirs:
            assert os.path.exists(dir_name), f"Production agent directory {dir_name} should exist"


class TestUtilities:
    """Test utility functions"""
    
    def test_string_operations(self):
        """Test basic string operations"""
        test_string = "data_engineer"
        assert test_string.replace("_", " ").title() == "Data Engineer"
    
    def test_list_operations(self):
        """Test basic list operations"""
        domains = ["data_engineer", "data_analytics", "digital_analytics"]
        assert len(domains) == 3
        assert "data_engineer" in domains
    
    def test_dict_operations(self):
        """Test basic dict operations"""
        config = {
            "catalog": "vagas_linkedin",
            "environment": "production"
        }
        assert config.get("catalog") == "vagas_linkedin"
        assert config.get("missing_key", "default") == "default"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
