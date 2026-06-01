"""
Tests for expression parsing edge cases and unparsed token scenarios.

Validates that the grammar improvements (function_call before identifier)
and consequence cleaning properly handle complex expressions without
leaving unparsed tokens.
"""

import pytest

from translator.semantic.conditionals import ConditionalParser, ConsequenceType


class TestFunctionCallParsing:
    """Test function calls are recognized correctly without ambiguity."""

    def test_simple_function_call(self):
        """Function call should be recognized, not left as unparsed identifier."""
        if_stmt = "if (upcase(name) = 'JOHN') then output;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert len(clauses) == 1
        assert "upcase" in clauses[0].condition
        assert clauses[0].consequence_type == ConsequenceType.OUTPUT

    def test_nested_function_calls(self):
        """Nested function calls should parse without confusion."""
        if_stmt = "if (substr(upcase(name), 1, 1) = 'A') then output;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert len(clauses) == 1
        assert "substr" in clauses[0].condition
        assert "upcase" in clauses[0].condition

    def test_function_with_multiple_args(self):
        """Function calls with multiple arguments should be recognized."""
        if_stmt = "if (substr(name, 1, 5) = 'SMITH') then x = 1;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert len(clauses) == 1
        assert "substr" in clauses[0].condition

    def test_function_call_in_consequence(self):
        """Function calls in consequences should be handled correctly."""
        if_stmt = "if (x > 10) then name = upcase(name);"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert len(clauses) == 1
        assert clauses[0].consequence_type == ConsequenceType.ASSIGNMENT
        # Consequence should be cleaned of trailing semicolon
        assert clauses[0].consequence == "name = upcase(name)"

    def test_multiple_function_calls_same_expression(self):
        """Multiple function calls in one expression should all be recognized."""
        if_stmt = "if (length(trim(name)) > 5) then output;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert len(clauses) == 1
        assert "length" in clauses[0].condition
        assert "trim" in clauses[0].condition


class TestConsequenceCleaning:
    """Test that consequence cleaning removes trailing semicolons and whitespace."""

    def test_consequence_with_trailing_semicolon(self):
        """Trailing semicolon should be removed from consequence."""
        if_stmt = "if (x = 1) then y = 10;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert clauses[0].consequence == "y = 10"
        # Should not have semicolon
        assert not clauses[0].consequence.endswith(";")

    def test_consequence_with_trailing_whitespace_and_semicolon(self):
        """Whitespace and semicolon should be cleaned."""
        if_stmt = "if (x = 1) then y = 10  ;  "
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert clauses[0].consequence == "y = 10"

    def test_multiple_clauses_all_cleaned(self):
        """All consequences in IF/ELSE chain should be cleaned."""
        if_stmt = "if (x = 1) then y = 10; else if (x = 2) then y = 20; else y = 30;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert len(clauses) == 3
        for clause in clauses:
            assert not clause.consequence.endswith(";")
            assert not clause.consequence.endswith(" ")

    def test_output_consequence_cleaned(self):
        """OUTPUT consequence should be cleaned."""
        if_stmt = "if (x > 100) then output;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert clauses[0].consequence == "output"

    def test_delete_consequence_cleaned(self):
        """DELETE consequence should be cleaned."""
        if_stmt = "if (x < 0) then delete;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert clauses[0].consequence == "delete"


class TestComplexExpressions:
    """Test complex expressions that could leave unparsed tokens."""

    def test_arithmetic_expression(self):
        """Arithmetic expressions should parse fully."""
        if_stmt = "if (x + y * z / 2 > 100) then result = x + y;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert "+" in clauses[0].condition
        assert "*" in clauses[0].condition
        assert "/" in clauses[0].condition

    def test_string_concatenation(self):
        """String concatenation with || should be handled."""
        if_stmt = "if (first_name || last_name = 'JOHNDOE') then output;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert "||" in clauses[0].condition

    def test_comparison_operators(self):
        """All comparison operators should work."""
        operators = ["=", "ne", "lt", "gt", "le", "ge", "<", ">", "<=", ">="]
        for op in operators:
            if_stmt = f"if (x {op} 10) then y = 1;"
            clauses = ConditionalParser.parse_if_statement(if_stmt)
            assert clauses is not None, f"Failed for operator: {op}"

    def test_in_operator(self):
        """IN operator should be recognized without leaving unparsed tokens."""
        if_stmt = "if (status in ('A', 'B', 'C')) then output;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert "in" in clauses[0].condition.lower()

    def test_contains_operator(self):
        """CONTAINS operator should be recognized."""
        if_stmt = "if (name contains 'SMITH') then keep = 1;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert "contains" in clauses[0].condition.lower()

    def test_logical_operators(self):
        """Logical operators AND/OR should be recognized."""
        if_stmt = "if ((x > 10) and (y < 20)) then output;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert "and" in clauses[0].condition.lower()

    def test_negation(self):
        """NOT operator should be recognized."""
        if_stmt = "if (not (x = 'ERROR')) then output;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert "not" in clauses[0].condition.lower()


class TestElseIfChaining:
    """Test ELSE IF chains with proper consequence cleaning."""

    def test_simple_else_if_chain(self):
        """Simple ELSE IF chain should parse all clauses."""
        if_stmt = "if (x = 1) then y = 10; else if (x = 2) then y = 20;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert len(clauses) == 2
        assert clauses[0].condition == "x = 1"
        assert clauses[1].condition == "x = 2"
        assert clauses[1].elif_chain is True

    def test_triple_else_if_chain(self):
        """Multiple ELSE IF clauses should all be recognized."""
        if_stmt = "if (x = 1) then a = 1; else if (x = 2) then a = 2; else if (x = 3) then a = 3; else a = 4;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert len(clauses) == 4
        # Check all consequences are cleaned
        assert clauses[0].consequence == "a = 1"
        assert clauses[1].consequence == "a = 2"
        assert clauses[2].consequence == "a = 3"
        assert clauses[3].consequence == "a = 4"

    def test_else_if_with_output_consequence(self):
        """ELSE IF with OUTPUT consequence should work."""
        if_stmt = "if (status = 'ERROR') then delete; else if (status = 'WARN') then output; else keep = 1;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert len(clauses) == 3
        assert clauses[0].consequence_type == ConsequenceType.DELETE
        assert clauses[1].consequence_type == ConsequenceType.OUTPUT
        assert clauses[2].consequence_type == ConsequenceType.ASSIGNMENT


class TestEdgeCases:
    """Test edge cases that might produce unparsed tokens."""

    def test_parenthesized_condition(self):
        """Deeply parenthesized conditions should parse."""
        if_stmt = "if (((x > 10) and (y < 20))) then z = 1;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None

    def test_function_call_without_args(self):
        """Function calls with no arguments should be recognized."""
        if_stmt = "if (today() = '01JUN2026'd) then flag = 1;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert "today" in clauses[0].condition.lower()

    def test_assignment_in_consequence_with_function(self):
        """Assignment in consequence with function call."""
        if_stmt = "if (x > 0) then result = sqrt(x);"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert clauses[0].consequence_type == ConsequenceType.ASSIGNMENT
        assert "sqrt" in clauses[0].consequence

    def test_consequence_with_multiple_statements_do_block(self):
        """DO block consequences should be recognized."""
        if_stmt = "if (error_flag = 1) then do; delete; flag_output = 'ERROR'; end;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert clauses[0].consequence_type == ConsequenceType.DO_BLOCK

    def test_missing_semicolon_in_middle_clause(self):
        """Handle missing semicolon between THEN and ELSE."""
        if_stmt = "if (x = 1) then y = 10 else y = 20;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        # Should still parse (semicolon may or may not be present)

    def test_numeric_literal_in_condition(self):
        """Numeric literals should not be treated as unparsed tokens."""
        if_stmt = "if (x > 3.14159) then y = 1;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None
        assert "3.14159" in clauses[0].condition

    def test_string_literal_in_condition(self):
        """String literals should be recognized."""
        if_stmt = "if (name = 'O\\'BRIEN') then keep = 1;"
        clauses = ConditionalParser.parse_if_statement(if_stmt)
        assert clauses is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
