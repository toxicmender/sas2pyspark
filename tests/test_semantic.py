"""
Unit tests for the semantic analysis module.
"""

import pytest

from translator.semantic import (
    DatasetMetadata,
    SemanticAnalyzer,
    SemanticContext,
    Variable,
    VariableScope,
    VariableType,
)


class TestVariable:
    """Tests for Variable class."""

    def test_variable_creation(self):
        """Test basic variable creation."""
        var = Variable(
            name="age",
            var_type=VariableType.NUMERIC,
            scope=VariableScope.DATA_STEP,
        )
        assert var.name == "age"
        assert var.var_type == VariableType.NUMERIC
        assert var.scope == VariableScope.DATA_STEP

    def test_variable_with_format(self):
        """Test variable with format specification."""
        var = Variable(
            name="salary",
            var_type=VariableType.NUMERIC,
            scope=VariableScope.DATA_STEP,
            format_spec="DOLLAR10.2",
        )
        assert var.format_spec == "DOLLAR10.2"


class TestDatasetMetadata:
    """Tests for DatasetMetadata class."""

    def test_dataset_creation(self):
        """Test dataset metadata creation."""
        metadata = DatasetMetadata(name="sales")
        assert metadata.name == "sales"
        assert len(metadata.variables) == 0

    def test_add_variable(self):
        """Test adding variables to dataset."""
        metadata = DatasetMetadata(name="sales")
        var = Variable(
            name="amount",
            var_type=VariableType.NUMERIC,
            scope=VariableScope.DATA_STEP,
        )
        metadata.add_variable(var)

        assert "amount" in metadata.variables
        assert metadata.variables["amount"] == var

    def test_get_variables(self):
        """Test getting variable list."""
        metadata = DatasetMetadata(name="sales")
        var1 = Variable("sales_id", VariableType.NUMERIC, VariableScope.DATA_STEP)
        var2 = Variable("amount", VariableType.NUMERIC, VariableScope.DATA_STEP)

        metadata.add_variable(var1)
        metadata.add_variable(var2)

        variables = metadata.get_variables()
        assert len(variables) == 2
        assert "sales_id" in variables
        assert "amount" in variables


class TestSemanticContext:
    """Tests for SemanticContext class."""

    def test_context_creation(self):
        """Test semantic context creation."""
        context = SemanticContext()
        assert len(context.datasets) == 0
        assert len(context.variables) == 0

    def test_declare_dataset(self):
        """Test declaring a dataset."""
        context = SemanticContext()
        metadata = context.declare_dataset("my_table")

        assert metadata.name == "my_table"
        assert "my_table" in context.datasets

    def test_get_dataset(self):
        """Test retrieving dataset metadata."""
        context = SemanticContext()
        context.declare_dataset("test_table")

        metadata = context.get_dataset("test_table")
        assert metadata is not None
        assert metadata.name == "test_table"

    def test_declare_variable(self):
        """Test declaring a variable."""
        context = SemanticContext()
        var = context.declare_variable("age", VariableType.NUMERIC)

        assert var.name == "age"
        assert var.var_type == VariableType.NUMERIC
        assert "age" in context.variables

    def test_mark_retained(self):
        """Test marking variable as retained."""
        context = SemanticContext()
        context.declare_variable("total", VariableType.NUMERIC)
        context.mark_retained("total")

        assert "total" in context.retained_variables
        assert context.variables["total"].var_type == VariableType.RETAINED

    def test_set_by_variables(self):
        """Test setting BY variables."""
        context = SemanticContext()
        context.set_by_variables(["customer_id", "date"])

        assert context.by_variables == ["customer_id", "date"]

    def test_is_automatic(self):
        """Test checking if variable is automatic."""
        context = SemanticContext()

        assert context.is_automatic("_N_")
        assert context.is_automatic("_ERROR_")
        assert not context.is_automatic("regular_var")


class TestSemanticAnalyzer:
    """Tests for SemanticAnalyzer class."""

    def test_analyzer_creation(self):
        """Test creating a semantic analyzer."""
        analyzer = SemanticAnalyzer()
        assert analyzer.context is not None

    def test_automatic_variables_initialized(self):
        """Test that automatic variables are initialized."""
        analyzer = SemanticAnalyzer()
        context = analyzer.get_context()

        assert "_N_" in context.automatic_variables
        assert "_ERROR_" in context.automatic_variables

    def test_analyze_data_step(self):
        """Test analyzing a DATA step."""
        analyzer = SemanticAnalyzer()
        analyzer.analyze_data_step("output_table")

        context = analyzer.get_context()
        assert context.current_scope == VariableScope.DATA_STEP
        assert "output_table" in context.datasets

    def test_analyze_proc_step(self):
        """Test analyzing a PROC step."""
        analyzer = SemanticAnalyzer()
        analyzer.analyze_proc_step("SORT")

        context = analyzer.get_context()
        assert context.current_scope == VariableScope.PROC_STEP

    def test_analyze_set_statement(self):
        """Test analyzing a SET statement."""
        analyzer = SemanticAnalyzer()

        # Create source dataset with variables
        analyzer.analyze_data_step("source_data")
        source_metadata = analyzer.get_context().declare_dataset("source_data")
        source_metadata.add_variable(
            Variable("col1", VariableType.NUMERIC, VariableScope.DATA_STEP)
        )
        source_metadata.add_variable(
            Variable("col2", VariableType.CHARACTER, VariableScope.DATA_STEP)
        )

        # Now analyze SET statement
        analyzer.analyze_set_statement(["source_data"])

        context = analyzer.get_context()
        assert "col1" in context.variables
        assert "col2" in context.variables

    def test_analyze_by_statement(self):
        """Test analyzing a BY statement."""
        analyzer = SemanticAnalyzer()
        analyzer.analyze_by_statement(["region", "product"])

        context = analyzer.get_context()
        assert context.by_variables == ["region", "product"]

    def test_get_variable_lineage(self):
        """Test getting variable lineage."""
        analyzer = SemanticAnalyzer()
        context = analyzer.get_context()

        var = context.declare_variable("amount", VariableType.NUMERIC)
        lineage = analyzer.get_variable_lineage("amount")

        assert lineage is not None
        assert lineage.name == "amount"

    def test_get_dataset_dependencies(self):
        """Test getting dataset dependencies."""
        analyzer = SemanticAnalyzer()
        context = analyzer.get_context()

        # Create datasets
        target = context.declare_dataset("output_table")
        target.source = "input_table"

        dependencies = analyzer.get_dataset_dependencies("output_table")
        assert "input_table" in dependencies


class TestSemanticContextIntegration:
    """Integration tests for semantic context."""

    def test_complex_data_flow(self):
        """Test complex data flow with multiple steps."""
        analyzer = SemanticAnalyzer()

        # Step 1: Read input
        analyzer.analyze_data_step("temp1")

        # Create source dataset with variables
        source_metadata = analyzer.get_context().declare_dataset("raw_data")
        source_metadata.add_variable(Variable("id", VariableType.NUMERIC, VariableScope.DATA_STEP))
        source_metadata.add_variable(
            Variable("amount", VariableType.NUMERIC, VariableScope.DATA_STEP)
        )

        analyzer.analyze_set_statement(["raw_data"])

        # Step 2: Verify variables are inherited
        context = analyzer.get_context()
        variables = context.variables
        assert len(variables) > 0
        assert "id" in variables
        assert "amount" in variables

    def test_multi_step_analysis(self):
        """Test analyzing multiple steps sequentially."""
        analyzer = SemanticAnalyzer()

        # DATA step 1
        analyzer.analyze_data_step("step1_output")
        analyzer.analyze_set_statement(["raw_input"])

        # PROC SORT
        analyzer.analyze_proc_step("SORT")
        analyzer.analyze_by_statement(["id"])

        context = analyzer.get_context()
        assert context.current_scope == VariableScope.PROC_STEP
        assert context.by_variables == ["id"]
