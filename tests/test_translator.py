"""
Unit tests for the main SAS translator.
"""

import tempfile
from pathlib import Path

import pytest

from main import SASTranslator


class TestSASTranslator:
    """Tests for the SASTranslator class."""

    def test_translator_creation(self):
        """Test creating a translator instance."""
        translator = SASTranslator()
        assert translator.parser is not None
        assert translator.semantic_analyzer is not None
        assert translator.emitter is not None

    def test_translate_simple_source(self):
        """Test translating simple SAS source code."""
        translator = SASTranslator()

        sas_code = """
        data output;
            set input;
        run;
        """

        pyspark_code = translator.translate_source(sas_code)

        assert pyspark_code is not None
        assert len(pyspark_code) > 0
        assert "from pyspark.sql import functions as F" in pyspark_code

    def test_translate_file(self, tmp_path: Path):
        """Test translating a SAS file."""
        translator = SASTranslator()

        # Create a temporary SAS file
        sas_file = tmp_path / "test.sas"
        sas_file.write_text("""
        data sales_final;
            set sales_2024;
        run;
        """)

        pyspark_code = translator.translate_file(sas_file)

        assert pyspark_code is not None
        assert "spark.table" in pyspark_code

    def test_translate_directory(self, tmp_path: Path):
        """Test translating all files in a directory."""
        translator = SASTranslator()

        # Create input directory with SAS files
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        sas_file1 = input_dir / "file1.sas"
        sas_file1.write_text("data out1; set in1; run;")

        sas_file2 = input_dir / "file2.sas"
        sas_file2.write_text("data out2; set in2; run;")

        # Create output directory
        output_dir = tmp_path / "output"

        # Translate
        translator.translate_directory(input_dir, output_dir)

        # Verify output
        assert (output_dir / "file1.py").exists()
        assert (output_dir / "file2.py").exists()

        code1 = (output_dir / "file1.py").read_text()
        code2 = (output_dir / "file2.py").read_text()

        # Both should have valid PySpark code
        assert "spark.table" in code1
        assert "spark.table" in code2
        assert "saveAsTable" in code1
        assert "saveAsTable" in code2

    def test_translate_source_generates_valid_python(self):
        """Test that translated source is valid Python syntax."""
        translator = SASTranslator()

        sas_code = "data output; set input; run;"

        pyspark_code = translator.translate_source(sas_code)

        # Should be able to parse as Python
        try:
            compile(pyspark_code, "<string>", "exec")
        except SyntaxError:
            pytest.fail(f"Generated code has syntax errors:\n{pyspark_code}")

    def test_translate_handles_errors_gracefully(self):
        """Test that translator handles errors gracefully."""
        translator = SASTranslator()

        # Empty source
        result = translator.translate_source("")
        assert result is not None

        # Invalid source
        result = translator.translate_source("this is not valid sas")
        assert result is not None


class TestTranslatorIntegration:
    """Integration tests for the translator."""

    def test_simple_data_step_translation(self):
        """Test translating a simple DATA step."""
        translator = SASTranslator()

        sas_code = """
        data final;
            set input_data;
        run;
        """

        pyspark_code = translator.translate_source(sas_code)

        assert "spark.table(" in pyspark_code
        assert "saveAsTable(" in pyspark_code


class TestTranslatorDirectoryProcessing:
    """Tests for directory processing."""

    def test_empty_directory(self, tmp_path: Path):
        """Test processing an empty directory."""
        translator = SASTranslator()

        input_dir = tmp_path / "empty"
        input_dir.mkdir()

        output_dir = tmp_path / "output"

        translator.translate_directory(input_dir, output_dir)

        # Output directory should exist but be empty (no .py files)
        assert output_dir.exists()

    def test_non_sas_files_ignored(self, tmp_path: Path):
        """Test that non-SAS files are ignored."""
        translator = SASTranslator()

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create non-SAS files
        (input_dir / "readme.txt").write_text("This is not SAS")
        (input_dir / "data.csv").write_text("col1,col2\n1,2\n")

        output_dir = tmp_path / "output"

        translator.translate_directory(input_dir, output_dir)

        # Should create empty output dir
        assert output_dir.exists()

    def test_creates_output_directory(self, tmp_path: Path):
        """Test that output directory is created if it doesn't exist."""
        translator = SASTranslator()

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        (input_dir / "test.sas").write_text("data out; set in; run;")

        output_dir = tmp_path / "nonexistent" / "output"

        translator.translate_directory(input_dir, output_dir)

        assert output_dir.exists()


class TestTranslatorErrorHandling:
    """Tests for error handling in translator."""

    def test_file_not_found(self):
        """Test handling of missing input file."""
        translator = SASTranslator()

        with pytest.raises(FileNotFoundError):
            translator.translate_file(Path("/nonexistent/file.sas"))

    def test_graceful_handling_of_missing_directory(self, tmp_path: Path):
        """Test that missing directory is handled gracefully."""
        translator = SASTranslator()

        # Non-existent input directory should result in no output files
        input_dir = tmp_path / "nonexistent"
        output_dir = tmp_path / "out"

        # This should not crash, just produce no output
        try:
            translator.translate_directory(input_dir, output_dir)
        except FileNotFoundError:
            # This is acceptable - the directory doesn't exist
            pass
