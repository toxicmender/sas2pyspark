"""
Unit tests for Databricks integration module.
"""

import pytest


class TestDatabricksIntegration:
    """Tests for Databricks connector."""

    def test_databricks_module_imports(self):
        """Test that Databricks module can be imported."""
        from translator.databricks import DatabricksConnector, create_spark_session_for_databricks

        assert DatabricksConnector is not None
        assert create_spark_session_for_databricks is not None

    def test_databricks_connector_initialization_requires_credentials(self):
        """Test that connector initialization requires credentials."""
        from translator.databricks import DatabricksConnector

        # This should fail without valid Databricks SDK
        with pytest.raises((ImportError, Exception)):
            DatabricksConnector("https://invalid.databricks.com", "invalid_token")

    def test_create_spark_session_available(self):
        """Test that Spark session creation function is available."""
        from translator.databricks import create_spark_session_for_databricks

        # Function should be callable (though it may fail without PySpark)
        assert callable(create_spark_session_for_databricks)
