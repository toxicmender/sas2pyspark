"""
Databricks integration module for SAS to PySpark translator.

Provides utilities for connecting to Databricks and executing translated code.
"""


class DatabricksConnector:
    """Manages connections to Databricks workspace."""

    def __init__(self, host: str, token: str):
        """
        Initialize Databricks connector.

        Args:
            host: Databricks workspace URL
            token: Personal access token
        """
        self.host = host
        self.token = token
        try:
            from databricks.sdk import WorkspaceClient

            self.client = WorkspaceClient(host=host, token=token)
        except ImportError:
            raise ImportError(
                "databricks-sdk is required. Install with: uv pip install databricks-sdk"
            )

    def test_connection(self) -> bool:
        """Test the connection to Databricks."""
        try:
            self.client.workspace.list("/")
            return True
        except Exception:
            return False

    def execute_script(self, script_path: str, spark_session) -> None:
        """
        Execute a translated PySpark script.

        Args:
            script_path: Path to the translated Python script
            spark_session: Active Spark session
        """
        with open(script_path, "r") as f:
            code = f.read()

        # Execute in the context of the provided spark session
        exec(code, {"spark": spark_session})

    def get_workspace_client(self):
        """Get the Databricks workspace client."""
        return self.client


def create_spark_session_for_databricks():
    """
    Create a Spark session configured for Databricks.

    Returns:
        SparkSession configured with Databricks settings
    """
    try:
        from pyspark.sql import SparkSession

        spark = (
            SparkSession.builder.appName("sas2pyspark_translator")
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config(
                "spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"
            )
            .getOrCreate()
        )

        return spark
    except ImportError:
        raise ImportError("pyspark is required. Install with: uv pip install pyspark>=3.5.0")


# Example usage
if __name__ == "__main__":
    # Note: This is example code only
    # In practice, you would use environment variables or a config file
    # to manage credentials

    print("Databricks Integration Module")
    print("=" * 50)
    print()
    print("To use Databricks integration:")
    print()
    print("from translator.databricks import DatabricksConnector")
    print("from main import SASTranslator")
    print()
    print("# Create translator and execute on Databricks")
    print("translator = SASTranslator()")
    print("pyspark_code = translator.translate_file('input.sas')")
    print()
    print("# Connect to Databricks")
    print("connector = DatabricksConnector(")
    print("    host='https://workspace.databricks.com',")
    print("    token='your-token-here'")
    print(")")
    print()
    print("# Test connection")
    print("if connector.test_connection():")
    print("    print('Connected to Databricks')")
