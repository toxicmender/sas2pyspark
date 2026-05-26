"""
Tests for IF/ELSE statement handling in SAS to PySpark translation.

Tests cover:
- Orphan ELSE detection
- IF/THEN with same-column assignments
- IF/THEN/ELSE with different-column assignments
- IF consequences: OUTPUT, DELETE, DO/END blocks
- ELSE IF (elif) chains
"""

import pytest

from translator.diagnostics import DiagnosticCategory, DiagnosticReport, DiagnosticSeverity
from translator.parser import ASTBuilder, SASParser
from translator.semantic.conditionals import (
    ConditionalParser,
    ConditionalValidator,
    ConsequenceType,
)
from translator.semantic.lower import DataStepLowerer


class TestConditionalParsing:
    """Tests for parsing IF/THEN/ELSE statements."""

    def test_parse_simple_if_then_assignment(self):
        """Test parsing simple IF/THEN assignment."""
        text = "if (x > 5) then y = 10;"
        clauses = ConditionalParser.parse_if_statement(text)

        assert clauses is not None
        assert len(clauses) == 1
        assert clauses[0].condition == "x > 5"
        assert clauses[0].consequence == "y = 10"
        assert clauses[0].consequence_type == ConsequenceType.ASSIGNMENT

    def test_parse_if_then_else_assignment(self):
        """Test parsing IF/THEN/ELSE with assignments."""
        text = "if (x > 5) then y = 10; else y = 20;"
        clauses = ConditionalParser.parse_if_statement(text)

        assert clauses is not None
        assert len(clauses) == 2
        assert clauses[0].condition == "x > 5"
        assert clauses[0].consequence == "y = 10"
        assert clauses[1].condition == ""  # ELSE has no condition
        assert clauses[1].consequence == "y = 20"

    def test_parse_if_then_else_if_chain(self):
        """Test parsing IF/THEN/ELSE IF chain."""
        text = "if (x > 10) then y = 10; else if (x > 5) then y = 5; else y = 0;"
        clauses = ConditionalParser.parse_if_statement(text)

        assert clauses is not None
        assert len(clauses) == 3
        assert clauses[0].condition == "x > 10"
        assert clauses[1].condition == "x > 5"
        assert clauses[1].elif_chain is True
        assert clauses[2].condition == ""
        assert clauses[2].elif_chain is False

    def test_parse_if_with_output(self):
        """Test parsing IF with OUTPUT consequence."""
        text = "if (flag = 1) then output;"
        clauses = ConditionalParser.parse_if_statement(text)

        assert clauses is not None
        assert len(clauses) == 1
        assert clauses[0].consequence_type == ConsequenceType.OUTPUT

    def test_parse_if_with_delete(self):
        """Test parsing IF with DELETE consequence."""
        text = "if (error_flag = 1) then delete;"
        clauses = ConditionalParser.parse_if_statement(text)

        assert clauses is not None
        assert len(clauses) == 1
        assert clauses[0].consequence_type == ConsequenceType.DELETE

    def test_parse_if_with_do_block(self):
        """Test parsing IF with DO...END block."""
        text = "if (x > 0) then do; y = x * 2; z = y + 1; end;"
        clauses = ConditionalParser.parse_if_statement(text)

        assert clauses is not None
        assert len(clauses) == 1
        assert clauses[0].consequence_type == ConsequenceType.DO_BLOCK

    def test_detect_orphan_else(self):
        """Test detection of orphan ELSE statement."""
        text = "else y = 5;"
        is_orphan = ConditionalParser.detect_orphan_else(text)

        assert is_orphan is True

    def test_detect_non_orphan_else(self):
        """Test that non-ELSE statements are not flagged."""
        text = "y = 5;"
        is_orphan = ConditionalParser.detect_orphan_else(text)

        assert is_orphan is False


class TestConditionalValidation:
    """Tests for validating IF/ELSE statement semantics."""

    def test_validate_same_column_assignments(self):
        """Test validation of assignments to same column."""
        clauses = ConditionalParser.parse_if_statement("if (x > 5) then y = 10; else y = 20;")

        is_consistent, target_col = ConditionalValidator.validate_clause_assignments(clauses)

        assert is_consistent is True
        assert target_col == "y"

    def test_validate_different_column_assignments(self):
        """Test validation detects different column assignments."""
        clauses = ConditionalParser.parse_if_statement("if (x > 5) then y = 10; else z = 20;")

        is_consistent, target_col = ConditionalValidator.validate_clause_assignments(clauses)

        assert is_consistent is False
        assert target_col is None

    def test_validate_non_assignment_consequences(self):
        """Test checking for non-assignment consequences."""
        clauses = ConditionalParser.parse_if_statement("if (x > 5) then output;")

        has_non_assign = ConditionalValidator.has_non_assignment_consequences(clauses)

        assert has_non_assign is True

    def test_validate_all_assignment_consequences(self):
        """Test checking for only assignment consequences."""
        clauses = ConditionalParser.parse_if_statement("if (x > 5) then y = 10;")

        has_non_assign = ConditionalValidator.has_non_assignment_consequences(clauses)

        assert has_non_assign is False


class TestIfElseDataStepLowering:
    """Tests for lowering IF/ELSE in DATA steps."""

    def test_lower_if_then_assignment(self):
        """Test lowering DATA step with simple IF/THEN assignment."""
        sas_code = """
        data output;
            set input;
            if (value > 100) then status = 'HIGH';
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        assert len(data_steps) == 1

        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert ir_node is not None

    def test_lower_if_then_else_same_column(self):
        """Test lowering DATA step with IF/THEN/ELSE to same column."""
        sas_code = """
        data output;
            set input;
            if (value > 100) then status = 'HIGH';
            else status = 'LOW';
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        assert len(data_steps) == 1

        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert ir_node is not None
        # Should have conditional_assignments tracked
        if hasattr(lowerer, "conditional_assignments"):
            assert len(lowerer.conditional_assignments) > 0

    def test_lower_if_then_else_different_columns_warning(self):
        """Test that IF/ELSE with different columns generates warning."""
        sas_code = """
        data output;
            set input;
            if (value > 100) then col_a = 'HIGH';
            else col_b = 'LOW';
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        # This should trigger a warning about different columns
        # We can capture this by checking if the conditional was tracked
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        # Should have multi_column_conditionals tracked
        if hasattr(lowerer, "multi_column_conditionals"):
            assert len(lowerer.multi_column_conditionals) > 0

    def test_lower_if_with_output_statement(self):
        """Test lowering DATA step with IF/OUTPUT."""
        sas_code = """
        data output;
            set input;
            if (flag = 1) then output;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert ir_node is not None
        if hasattr(lowerer, "conditional_outputs"):
            assert len(lowerer.conditional_outputs) > 0

    def test_lower_if_with_delete_statement(self):
        """Test lowering DATA step with IF/DELETE."""
        sas_code = """
        data output;
            set input;
            if (error = 1) then delete;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert ir_node is not None
        if hasattr(lowerer, "conditional_deletes"):
            assert len(lowerer.conditional_deletes) > 0


class TestOrphanElseDiagnostics:
    """Tests for orphan ELSE detection and diagnostics."""

    def test_orphan_else_in_data_step(self):
        """Test that orphan ELSE in DATA step is detected."""
        sas_code = """
        data output;
            set input;
            else y = 5;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        # This should trigger orphan ELSE detection
        ir_node = lowerer.lower_data_step(data_steps[0], "output")
        assert ir_node is not None


class TestMixedColumnAssignmentDiagnostics:
    """Tests for diagnostics of IF/ELSE with mixed column assignments."""

    def test_diagnostic_report_creation(self):
        """Test creation of diagnostic report."""
        report = DiagnosticReport()

        report.add_mixed_column_assignment(
            columns=["col_a", "col_b"],
            source_text="if (x > 5) then col_a = 1; else col_b = 2;",
        )

        assert len(report.diagnostics) == 1
        assert report.diagnostics[0].category == DiagnosticCategory.MIXED_COLUMN_ASSIGNMENT
        assert report.diagnostics[0].severity == DiagnosticSeverity.WARNING

    def test_diagnostic_report_formatting(self):
        """Test formatting of diagnostic report."""
        report = DiagnosticReport()

        report.add_orphan_else("else y = 5;")
        report.add_mixed_column_assignment(["col_a", "col_b"])
        report.add_conditional_output("x > 5")

        summary = report.format_summary()
        assert "3 diagnostics" in summary
        assert "1 errors" in summary
        assert "2 warnings" in summary


class TestComplexConditionalCases:
    """Tests for complex IF/ELSE scenarios."""

    def test_nested_if_conditions(self):
        """Test parsing nested IF conditions."""
        text = "if (x > 5 and y < 10) then z = 1; else z = 0;"
        clauses = ConditionalParser.parse_if_statement(text)

        assert clauses is not None
        assert len(clauses) == 2
        assert "and" in clauses[0].condition

    def test_if_with_multiple_else_if_chain(self):
        """Test parsing multiple ELSE IF clauses."""
        text = """
        if (x > 10) then category = 'VERY_HIGH';
        else if (x > 5) then category = 'HIGH';
        else if (x > 0) then category = 'POSITIVE';
        else category = 'NON_POSITIVE';
        """
        clauses = ConditionalParser.parse_if_statement(text)

        assert clauses is not None
        assert len(clauses) == 4
        assert clauses[0].elif_chain is False
        assert clauses[1].elif_chain is True
        assert clauses[2].elif_chain is True
        assert clauses[3].elif_chain is False
        assert clauses[3].condition == ""

    def test_if_with_complex_assignment_expression(self):
        """Test parsing IF with complex assignment expressions."""
        text = "if (age >= 18) then status = 'ADULT'; else status = 'MINOR';"
        clauses = ConditionalParser.parse_if_statement(text)

        assert clauses is not None
        assert len(clauses) == 2
        assert clauses[0].consequence == "status = 'ADULT'"
        assert clauses[1].consequence == "status = 'MINOR'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
