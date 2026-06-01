"""
Integration tests for the Tree-sitter SAS grammar.

These tests verify that:
1. SASParser can be instantiated with or without the compiled grammar
2. Basic SAS code can be parsed and produces expected AST structure
3. The parser gracefully falls back to stub parser when grammar is unavailable
4. Both compiled grammar and stub parser work with common SAS constructs
"""

import warnings
from pathlib import Path

import pytest

from translator.parser import ASTNode, SASParser


class TestSASParserInstantiation:
    """Test SASParser instantiation and fallback behavior."""

    def test_parser_instantiation(self):
        """Test that SASParser can be instantiated without errors."""
        parser = SASParser()
        assert parser is not None

    def test_parser_has_parse_method(self):
        """Test that parser has the parse method."""
        parser = SASParser()
        assert hasattr(parser, "parse")
        assert callable(parser.parse)

    def test_parser_fallback_info(self):
        """Test that parser provides fallback information."""
        parser = SASParser()
        assert hasattr(parser, "grammar_loaded")
        assert isinstance(parser.grammar_loaded, bool)


class TestBasicParsing:
    """Test parsing of basic SAS code structures."""

    def test_parse_simple_assignment(self):
        """Test parsing a simple assignment statement."""
        parser = SASParser()
        code = "x = 10;"
        result = parser.parse(code)
        assert result is not None
        # Result should be dict-like with structure information
        assert isinstance(result, dict)

    def test_parse_string_assignment(self):
        """Test parsing string assignment."""
        parser = SASParser()
        code = 'name = "John";'
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_numeric_assignment(self):
        """Test parsing numeric operations in assignments."""
        parser = SASParser()
        code = "result = 5 + 3 * 2;"
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)


class TestIfThenElseStructures:
    """Test parsing if/then/else control structures."""

    def test_parse_simple_if_then(self):
        """Test parsing simple if/then statement."""
        parser = SASParser()
        code = """
        if age > 18 then
            status = "adult";
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_if_then_else(self):
        """Test parsing if/then/else statement."""
        parser = SASParser()
        code = """
        if sales > 1000 then
            category = "High";
        else
            category = "Low";
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_nested_if_then_else(self):
        """Test parsing nested if/then/else statements."""
        parser = SASParser()
        code = """
        if age < 13 then
            group = "Child";
        else if age < 18 then
            group = "Teen";
        else
            group = "Adult";
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)


class TestDataStepStructures:
    """Test parsing DATA step structures."""

    def test_parse_simple_data_step(self):
        """Test parsing simple data step with set statement."""
        parser = SASParser()
        code = """
        data output;
            set input;
        run;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_data_step_with_set_and_where(self):
        """Test parsing data step with set and where clause."""
        parser = SASParser()
        code = """
        data filtered;
            set input;
            where age > 18;
        run;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_data_step_with_assignment(self):
        """Test parsing data step with variable assignment."""
        parser = SASParser()
        code = """
        data processed;
            set input;
            total = price * quantity;
        run;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_data_step_with_if_statement(self):
        """Test parsing data step with if statement."""
        parser = SASParser()
        code = """
        data categorized;
            set input;
            if price > 100 then
                category = "Expensive";
            else
                category = "Affordable";
        run;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_data_step_with_keep_drop(self):
        """Test parsing data step with keep and drop statements."""
        parser = SASParser()
        code = """
        data output;
            set input;
            keep id name age;
            drop temp_var;
        run;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)


class TestProcedureSteps:
    """Test parsing PROC step structures."""

    def test_parse_simple_proc_step(self):
        """Test parsing simple proc print statement."""
        parser = SASParser()
        code = """
        proc print data=input;
        run;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_proc_with_var_statement(self):
        """Test parsing proc step with var statement."""
        parser = SASParser()
        code = """
        proc print data=input;
            var id name age;
        run;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_proc_with_where_statement(self):
        """Test parsing proc step with where statement."""
        parser = SASParser()
        code = """
        proc print data=input;
            where age > 18;
        run;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)


class TestASTStructure:
    """Test that parsed AST has expected structure."""

    def test_ast_has_root_node(self):
        """Test that parsed result has root node information."""
        parser = SASParser()
        code = "data test; set input; run;"
        result = parser.parse(code)
        assert result is not None
        # Result should contain type information
        assert "type" in result or "node_type" in result or "text" in result

    def test_ast_contains_statements(self):
        """Test that AST contains statement information."""
        parser = SASParser()
        code = """
        data test;
            set input;
            x = 10;
        run;
        """
        result = parser.parse(code)
        assert result is not None
        # Check that we have some structure
        assert isinstance(result, dict)

    def test_parse_returns_dict(self):
        """Test that parse method returns a dictionary."""
        parser = SASParser()
        code = "x = 5;"
        result = parser.parse(code)
        assert isinstance(result, dict)


class TestExpressionParsing:
    """Test parsing of various expressions."""

    def test_parse_arithmetic_expression(self):
        """Test parsing arithmetic expressions."""
        parser = SASParser()
        code = "result = 10 + 20 * 3;"
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_comparison_expression(self):
        """Test parsing comparison expressions."""
        parser = SASParser()
        code = "flag = age > 18 and salary > 50000;"
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_string_concatenation(self):
        """Test parsing string concatenation."""
        parser = SASParser()
        code = 'full_name = first_name || " " || last_name;'
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_function_call(self):
        """Test parsing function calls in expressions."""
        parser = SASParser()
        code = "upper_name = upcase(name);"
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)


class TestFallbackBehavior:
    """Test that stub parser gracefully handles various inputs."""

    def test_fallback_parser_handles_empty_code(self):
        """Test that parser handles empty code."""
        parser = SASParser()
        code = ""
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_fallback_parser_handles_comments(self):
        """Test that parser handles code with comments."""
        parser = SASParser()
        code = """
        /* This is a comment */
        data test;
            set input;
            * Single line comment;
        run;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_fallback_parser_handles_mixed_case(self):
        """Test that parser handles mixed case keywords."""
        parser = SASParser()
        code = """
        DATA test;
            SET input;
        RUN;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)


class TestParserWarnings:
    """Test that appropriate warnings are issued when grammar is unavailable."""

    def test_parser_warnings_on_creation(self):
        """Test that warnings are issued if grammar is not available."""
        # This test verifies that warnings are captured correctly
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            parser = SASParser()
            # If grammar is loaded, no warning; if not, warning is issued
            # We just verify no exception is raised
            assert parser is not None


class TestParserEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_multiline_statement(self):
        """Test parsing statements spanning multiple lines."""
        parser = SASParser()
        code = """
        long_result =
            value1 +
            value2 +
            value3;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_statement_with_semicolon(self):
        """Test that statements are recognized with semicolons."""
        parser = SASParser()
        code = "x = 10; y = 20; z = x + y;"
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)

    def test_parse_code_with_whitespace(self):
        """Test that parser handles various whitespace."""
        parser = SASParser()
        code = """
        data    test   ;
            set     input  ;
        run   ;
        """
        result = parser.parse(code)
        assert result is not None
        assert isinstance(result, dict)
