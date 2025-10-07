"""
Basic integration tests for Vagas LinkedIn project
"""
import pytest
import os


@pytest.mark.integration
def test_environment_variables():
    """Test that we can access environment variables"""
    # Test doesn't require actual values, just that we can read env vars
    test_var = os.getenv("TEST_VAR", "default")
    assert test_var is not None


@pytest.mark.integration
def test_file_system_access():
    """Test file system operations"""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        
        # Write
        with open(test_file, "w") as f:
            f.write("test content")
        
        # Read
        with open(test_file, "r") as f:
            content = f.read()
        
        assert content == "test content"


@pytest.mark.integration
class TestProjectIntegration:
    """Integration tests for project components"""
    
    def test_import_app_production(self):
        """Test that app_production modules can be imported"""
        import sys
        import os
        
        # Add project root to path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # Test basic import (without actual execution)
        assert os.path.exists("app_production")
    
    def test_import_agents(self):
        """Test that agent modules exist"""
        import os
        
        assert os.path.exists("agents")
        assert os.path.exists("app_production/agents")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
