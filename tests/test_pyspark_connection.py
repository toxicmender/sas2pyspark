from __future__ import annotations

import os
import shutil

import pytest

pyspark = pytest.importorskip("pyspark")

if not os.environ.get("JAVA_HOME") and shutil.which("java") is None:
    pytest.skip("Java is required to start Spark", allow_module_level=True)

from pyspark.sql import SparkSession  # noqa: E402


def test_pyspark_connection():
    spark = (
        SparkSession.builder.master("local[1]")
        .appName("sas2pyspark-test")
        .getOrCreate()
    )
    try:
        assert spark.range(1).count() == 1
    finally:
        spark.stop()
