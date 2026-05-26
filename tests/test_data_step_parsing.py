"""
Unit tests for DATA step statement parsing.

Tests the enhanced stub parser's ability to recognize and parse
DATA step statements like MERGE, BY, KEEP, DROP, LENGTH, FORMAT, INFORMAT.
"""

import pytest

from translator.parser import ASTBuilder, SASParser


class TestDataStepParsing:
    """Tests for DATA step statement parsing."""

    def test_parse_set_statement(self):
        """Test parsing SET statement."""
        sas_code = """
        data output;
            set input;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        assert ast_dict is not None
        assert ast_dict["type"] == "source_file"
        assert len(ast_dict["children"]) > 0

        data_step = ast_dict["children"][0]
        assert data_step["type"] == "data_step"
        assert len(data_step["children"]) > 0

        # Find the SET statement
        set_stmts = [child for child in data_step["children"] if child["type"] == "set_statement"]
        assert len(set_stmts) > 0

    def test_parse_merge_statement(self):
        """Test parsing MERGE statement."""
        sas_code = """
        data output;
            merge dataset1 dataset2;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        merge_stmts = [
            child for child in data_step["children"] if child["type"] == "merge_statement"
        ]
        assert len(merge_stmts) > 0

    def test_parse_by_statement(self):
        """Test parsing BY statement."""
        sas_code = """
        data output;
            set input;
            by group_var;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        by_stmts = [child for child in data_step["children"] if child["type"] == "by_statement"]
        assert len(by_stmts) > 0

    def test_parse_keep_statement(self):
        """Test parsing KEEP statement."""
        sas_code = """
        data output;
            set input;
            keep var1 var2 var3;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        keep_stmts = [child for child in data_step["children"] if child["type"] == "keep_statement"]
        assert len(keep_stmts) > 0

    def test_parse_drop_statement(self):
        """Test parsing DROP statement."""
        sas_code = """
        data output;
            set input;
            drop unwanted_var;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        drop_stmts = [child for child in data_step["children"] if child["type"] == "drop_statement"]
        assert len(drop_stmts) > 0

    def test_parse_length_statement(self):
        """Test parsing LENGTH statement."""
        sas_code = """
        data output;
            length var1 $50 var2 8;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        length_stmts = [
            child for child in data_step["children"] if child["type"] == "length_statement"
        ]
        assert len(length_stmts) > 0

    def test_parse_format_statement(self):
        """Test parsing FORMAT statement."""
        sas_code = """
        data output;
            format date_var DATE9. amount DOLLAR10.2;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        format_stmts = [
            child for child in data_step["children"] if child["type"] == "format_statement"
        ]
        assert len(format_stmts) > 0

    def test_parse_informat_statement(self):
        """Test parsing INFORMAT statement."""
        sas_code = """
        data output;
            informat date_var DATE9. amount DOLLAR10.2;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        informat_stmts = [
            child for child in data_step["children"] if child["type"] == "informat_statement"
        ]
        assert len(informat_stmts) > 0

    def test_parse_retain_statement(self):
        """Test parsing RETAIN statement."""
        sas_code = """
        data output;
            retain counter 0;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        retain_stmts = [
            child for child in data_step["children"] if child["type"] == "retain_statement"
        ]
        assert len(retain_stmts) > 0

    def test_parse_output_statement(self):
        """Test parsing OUTPUT statement."""
        sas_code = """
        data output;
            set input;
            if status = 'ACTIVE' then output;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        output_stmts = [
            child for child in data_step["children"] if child["type"] == "output_statement"
        ]
        assert len(output_stmts) > 0

    def test_parse_delete_statement(self):
        """Test parsing DELETE statement."""
        sas_code = """
        data output;
            set input;
            if status = 'INACTIVE' then delete;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        # DELETE is typically part of an if-then statement
        # But we should still be able to find related content
        assert len(data_step["children"]) > 0

    def test_parse_multiple_statements(self):
        """Test parsing multiple DATA step statements together."""
        sas_code = """
        data output;
            merge dataset1 dataset2;
            by id;
            length name $100;
            format date_var DATE9.;
            if status = 'ACTIVE' then do;
                new_var = existing_var * 2;
                output;
            end;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]

        # Check for various statements
        types_found = {child["type"] for child in data_step["children"]}

        # Should find at least merge, by, length, format
        assert "merge_statement" in types_found
        assert "by_statement" in types_found
        assert "length_statement" in types_found
        assert "format_statement" in types_found

    def test_parse_complex_data_step(self):
        """Test parsing a complex DATA step with mixed statement types."""
        sas_code = """
        data sales_final;
            merge sales1 sales2;
            by region;
            keep region sales_amount date;
            drop tax_code;
            length region $20 sales_amount 12;
            format sales_amount DOLLAR10.2 date DATE9.;
            if sales_amount > 1000 then category = 'HIGH';
            else category = 'LOW';
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        assert ast_dict is not None
        data_step = ast_dict["children"][0]

        # Verify it has children (statements)
        assert len(data_step["children"]) > 0

        # Collect all statement types found
        statement_types = [child["type"] for child in data_step["children"]]

        # Should have recognized most statements
        assert "merge_statement" in statement_types
        assert "by_statement" in statement_types
        assert any(t in statement_types for t in ["keep_statement", "drop_statement"])
        assert "length_statement" in statement_types
        assert "format_statement" in statement_types

    def test_ast_builder_with_parsed_data_step(self):
        """Test building typed AST from parsed DATA step."""
        sas_code = """
        data output;
            set input;
            keep var1 var2;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        # Find data steps
        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        assert len(data_steps) > 0

        data_step = data_steps[0]
        # Should have children (parsed statements)
        assert len(data_step.children) > 0


class TestDataStepStatementExtraction:
    """Tests for extraction of specific statements from DATA steps."""

    def test_extract_set_statements(self):
        """Test extracting SET statements from parsed AST."""
        sas_code = """
        data output;
            set input1 input2;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        data_step = ast_dict["children"][0]

        set_stmts = [child for child in data_step["children"] if child["type"] == "set_statement"]
        assert len(set_stmts) == 1
        assert "set" in set_stmts[0]["text"].lower()
        assert "input1" in set_stmts[0]["text"].lower()

    def test_extract_merge_statements(self):
        """Test extracting MERGE statements from parsed AST."""
        sas_code = """
        data output;
            merge left right;
            by key;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        data_step = ast_dict["children"][0]

        merge_stmts = [
            child for child in data_step["children"] if child["type"] == "merge_statement"
        ]
        assert len(merge_stmts) == 1
        assert "merge" in merge_stmts[0]["text"].lower()
        assert "left" in merge_stmts[0]["text"].lower()

    def test_extract_keep_drop_statements(self):
        """Test extracting KEEP and DROP statements."""
        sas_code = """
        data output;
            set input;
            keep important_var;
            drop unimportant_var;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        data_step = ast_dict["children"][0]

        keep_stmts = [child for child in data_step["children"] if child["type"] == "keep_statement"]
        drop_stmts = [child for child in data_step["children"] if child["type"] == "drop_statement"]

        assert len(keep_stmts) == 1
        assert len(drop_stmts) == 1

    def test_extract_length_format_informat(self):
        """Test extracting LENGTH, FORMAT, and INFORMAT statements."""
        sas_code = """
        data output;
            length name $50;
            format salary DOLLAR10.2;
            informat start_date DATE9.;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        data_step = ast_dict["children"][0]

        length_stmts = [
            child for child in data_step["children"] if child["type"] == "length_statement"
        ]
        format_stmts = [
            child for child in data_step["children"] if child["type"] == "format_statement"
        ]
        informat_stmts = [
            child for child in data_step["children"] if child["type"] == "informat_statement"
        ]

        assert len(length_stmts) == 1
        assert len(format_stmts) == 1
        assert len(informat_stmts) == 1


class TestDataStepParsingEdgeCases:
    """Tests for edge cases in DATA step parsing."""

    def test_empty_data_step(self):
        """Test parsing empty DATA step."""
        sas_code = "data output; run;"
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        assert ast_dict is not None
        assert len(ast_dict["children"]) > 0

    def test_data_step_with_comments(self):
        """Test parsing DATA step with comments."""
        sas_code = """
        data output;
            /* This is a comment */
            set input;
            * Another comment;
            keep var1;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        data_step = ast_dict["children"][0]
        # Should still parse despite comments
        assert len(data_step["children"]) > 0

    def test_data_step_case_insensitive(self):
        """Test that DATA step parsing is case-insensitive."""
        sas_code_upper = """
        DATA OUTPUT;
            SET INPUT;
            KEEP VAR1;
        RUN;
        """
        sas_code_lower = """
        data output;
            set input;
            keep var1;
        run;
        """
        sas_code_mixed = """
        Data Output;
            Set Input;
            Keep Var1;
        Run;
        """

        parser = SASParser()

        ast_upper = parser.parse(sas_code_upper)
        ast_lower = parser.parse(sas_code_lower)
        ast_mixed = parser.parse(sas_code_mixed)

        # All should parse successfully
        assert ast_upper is not None
        assert ast_lower is not None
        assert ast_mixed is not None

        # Should have same structure
        assert len(ast_upper["children"]) > 0
        assert len(ast_lower["children"]) > 0
        assert len(ast_mixed["children"]) > 0

    def test_multiple_data_steps(self):
        """Test parsing multiple DATA steps."""
        sas_code = """
        data step1;
            set input;
            keep var1;
        run;

        data step2;
            set step1;
            format var1 $20.;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)

        # Should have two data steps
        data_steps = [child for child in ast_dict["children"] if child["type"] == "data_step"]
        assert len(data_steps) == 2
