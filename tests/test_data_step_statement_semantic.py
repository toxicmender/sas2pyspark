"""
Tests for DATA step statement parsing and semantic lowering.

Verifies that DATA step statements (MERGE, BY, KEEP, DROP, LENGTH, FORMAT, INFORMAT, etc.)
are correctly parsed and made available to the semantic pass for IR generation.
"""

import pytest

from translator.parser import ASTBuilder, SASParser
from translator.semantic.lower import DataStepLowerer


class TestDataStepStatementParsing:
    """Tests for parsing DATA step statements in the AST."""

    def test_statements_recognized_in_ast(self):
        """Test that all DATA step statements are recognized in the AST."""
        sas_code = """
        data output;
            merge left right;
            by id;
            keep name value;
            drop temp;
            length name $100;
            format date DATE9.;
            informat start_date DATE9.;
            retain counter 0;
            if value > 0 then output;
            if status = 'INACTIVE' then delete;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        assert len(data_steps) == 1

        data_step = data_steps[0]
        statement_types = {child.node_type for child in data_step.children}

        # Verify all expected statement types are in the AST
        expected_types = {
            "merge_statement",
            "by_statement",
            "keep_statement",
            "drop_statement",
            "length_statement",
            "format_statement",
            "informat_statement",
            "retain_statement",
        }

        for expected_type in expected_types:
            assert expected_type in statement_types, f"Missing {expected_type} in AST"

    def test_merge_statement_parsed_correctly(self):
        """Test that MERGE statement is parsed with dataset names."""
        sas_code = """
        data output;
            merge dataset1 dataset2 dataset3;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        merge_stmts = ASTBuilder.find_nodes(data_steps[0], "merge_statement")

        assert len(merge_stmts) == 1
        merge_stmt = merge_stmts[0]
        assert "dataset1" in merge_stmt.text.lower()
        assert "dataset2" in merge_stmt.text.lower()
        assert "dataset3" in merge_stmt.text.lower()

    def test_by_statement_parsed_correctly(self):
        """Test that BY statement is parsed with variable names."""
        sas_code = """
        data output;
            set input;
            by region descending date;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        by_stmts = ASTBuilder.find_nodes(data_steps[0], "by_statement")

        assert len(by_stmts) == 1
        by_stmt = by_stmts[0]
        assert "region" in by_stmt.text.lower()
        assert "date" in by_stmt.text.lower()

    def test_keep_statement_parsed_correctly(self):
        """Test that KEEP statement is parsed with column names."""
        sas_code = """
        data output;
            set input;
            keep id name salary department;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        keep_stmts = ASTBuilder.find_nodes(data_steps[0], "keep_statement")

        assert len(keep_stmts) == 1
        keep_stmt = keep_stmts[0]
        text_lower = keep_stmt.text.lower()
        assert "id" in text_lower
        assert "name" in text_lower
        assert "salary" in text_lower
        assert "department" in text_lower

    def test_drop_statement_parsed_correctly(self):
        """Test that DROP statement is parsed with column names."""
        sas_code = """
        data output;
            set input;
            drop temporary_var debug_flag;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        drop_stmts = ASTBuilder.find_nodes(data_steps[0], "drop_statement")

        assert len(drop_stmts) == 1
        drop_stmt = drop_stmts[0]
        text_lower = drop_stmt.text.lower()
        assert "temporary_var" in text_lower
        assert "debug_flag" in text_lower

    def test_length_statement_parsed_correctly(self):
        """Test that LENGTH statement is parsed with variable declarations."""
        sas_code = """
        data output;
            length name $100 age 8 salary 12.2;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        length_stmts = ASTBuilder.find_nodes(data_steps[0], "length_statement")

        assert len(length_stmts) == 1
        length_stmt = length_stmts[0]
        text_lower = length_stmt.text.lower()
        assert "name" in text_lower
        assert "age" in text_lower
        assert "salary" in text_lower

    def test_format_statement_parsed_correctly(self):
        """Test that FORMAT statement is parsed with format specifications."""
        sas_code = """
        data output;
            format date_var DATE9. amount DOLLAR10.2 percent 4.1;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        format_stmts = ASTBuilder.find_nodes(data_steps[0], "format_statement")

        assert len(format_stmts) == 1
        format_stmt = format_stmts[0]
        text = format_stmt.text
        assert "date_var" in text.lower()
        assert "amount" in text.lower()

    def test_informat_statement_parsed_correctly(self):
        """Test that INFORMAT statement is parsed with informat specifications."""
        sas_code = """
        data output;
            informat date_var DATE9. start_date DATETIME21.;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        informat_stmts = ASTBuilder.find_nodes(data_steps[0], "informat_statement")

        assert len(informat_stmts) == 1
        informat_stmt = informat_stmts[0]
        text_lower = informat_stmt.text.lower()
        assert "date_var" in text_lower
        assert "start_date" in text_lower

    def test_retain_statement_parsed_correctly(self):
        """Test that RETAIN statement is parsed with variable specifications."""
        sas_code = """
        data output;
            retain counter 0 running_total 0 group '';
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        retain_stmts = ASTBuilder.find_nodes(data_steps[0], "retain_statement")

        assert len(retain_stmts) == 1
        retain_stmt = retain_stmts[0]
        text_lower = retain_stmt.text.lower()
        assert "counter" in text_lower
        assert "running_total" in text_lower


class TestDataStepStatementSemanticProcessing:
    """Tests for processing DATA step statements in the semantic pass."""

    def test_merge_statement_processed_by_lowerer(self):
        """Test that lowerer processes MERGE statement."""
        sas_code = """
        data output;
            merge left right;
            by id;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        # Process the data step
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        # Verify merge datasets were captured
        assert len(lowerer.merge_datasets) > 0
        assert "left" in lowerer.merge_datasets
        assert "right" in lowerer.merge_datasets

    def test_by_statement_processed_by_lowerer(self):
        """Test that lowerer processes BY statement."""
        sas_code = """
        data output;
            set input;
            by region, date;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        # Process the data step
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        # Verify BY variables were captured
        assert len(lowerer.by_variables) > 0
        assert "region" in lowerer.by_variables
        assert "date" in lowerer.by_variables

    def test_keep_statement_processed_by_lowerer(self):
        """Test that lowerer processes KEEP statement."""
        sas_code = """
        data output;
            set input;
            keep id, name, salary;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        # Process the data step
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        # Verify KEEP columns were captured
        assert lowerer.keep_columns is not None
        assert "id" in lowerer.keep_columns
        assert "name" in lowerer.keep_columns
        assert "salary" in lowerer.keep_columns

    def test_drop_statement_processed_by_lowerer(self):
        """Test that lowerer processes DROP statement."""
        sas_code = """
        data output;
            set input;
            drop temp, debug;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        # Process the data step
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        # Verify DROP columns were captured
        assert lowerer.drop_columns is not None
        assert "temp" in lowerer.drop_columns
        assert "debug" in lowerer.drop_columns

    def test_length_statement_processed_by_lowerer(self):
        """Test that lowerer processes LENGTH statement."""
        sas_code = """
        data output;
            length name $50 age 8;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        # This should not raise an error
        ir_node = lowerer.lower_data_step(data_steps[0], "output")
        assert ir_node is not None

    def test_format_statement_processed_by_lowerer(self):
        """Test that lowerer processes FORMAT statement."""
        sas_code = """
        data output;
            format date_var DATE9.;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        # This should not raise an error
        ir_node = lowerer.lower_data_step(data_steps[0], "output")
        assert ir_node is not None

    def test_informat_statement_processed_by_lowerer(self):
        """Test that lowerer processes INFORMAT statement."""
        sas_code = """
        data output;
            informat date_var DATE9.;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        # This should not raise an error
        ir_node = lowerer.lower_data_step(data_steps[0], "output")
        assert ir_node is not None

    def test_retain_statement_processed_by_lowerer(self):
        """Test that lowerer processes RETAIN statement."""
        sas_code = """
        data output;
            retain counter 0;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        # This should not raise an error
        ir_node = lowerer.lower_data_step(data_steps[0], "output")
        assert ir_node is not None


class TestComplexDataStepStatementCombinations:
    """Tests for complex combinations of DATA step statements."""

    def test_merge_with_by_and_keep(self):
        """Test MERGE with BY and KEEP statements."""
        sas_code = """
        data sales_report;
            merge sales targets;
            by quarter;
            keep quarter, target, actual;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "sales_report")

        # All statements should be processed
        assert len(lowerer.merge_datasets) == 2
        assert len(lowerer.by_variables) == 1
        assert lowerer.keep_columns is not None
        assert len(lowerer.keep_columns) == 3

    def test_set_with_keep_drop_format(self):
        """Test SET with KEEP, DROP, and FORMAT statements."""
        sas_code = """
        data processed;
            set raw_data;
            drop temp_var;
            keep id, name, date_field;
            format date_field DATE9.;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "processed")

        # All statements should be processed
        assert len(lowerer.input_datasets) == 1
        assert lowerer.drop_columns is not None
        assert lowerer.keep_columns is not None
        assert "id" in lowerer.keep_columns

    def test_set_with_length_and_informat(self):
        """Test SET with LENGTH and INFORMAT statements."""
        sas_code = """
        data imported;
            set source;
            length name $100;
            informat start_date DATE9.;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "imported")
        assert ir_node is not None

    def test_multiple_keep_drop_statements(self):
        """Test DATA step with multiple KEEP/DROP statements."""
        sas_code = """
        data output;
            set input;
            keep var1 var2;
            drop temp;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        # The last DROP statement should override previous KEEP (in SAS semantics)
        # But our parser should capture both
        assert lowerer.keep_columns is not None
        assert lowerer.drop_columns is not None

    def test_all_statement_types_in_one_step(self):
        """Test DATA step with all supported statement types."""
        sas_code = """
        data comprehensive;
            merge ds1 ds2;
            by key_var;
            keep id value;
            drop temp;
            length id 8 value $20;
            format date_field DATE9.;
            informat input_date DATE9.;
            retain counter 0;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "comprehensive")

        # Verify all statement types were processed without errors
        assert len(lowerer.merge_datasets) == 2
        assert len(lowerer.by_variables) == 1
        assert lowerer.keep_columns is not None
        assert lowerer.drop_columns is not None
        assert ir_node is not None


class TestStatementExtractionFromAST:
    """Tests for extracting specific statements from parsed AST."""

    def test_can_extract_all_statement_types_from_ast(self):
        """Test that all statement types can be extracted from the AST."""
        sas_code = """
        data test;
            set data1;
            merge data2;
            by group;
            keep col1 col2;
            drop col3;
            length col1 $50;
            format col2 12.2;
            informat col4 $20.;
            retain total 0;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        assert len(data_steps) == 1

        # Extract all statement types
        set_stmts = ASTBuilder.find_nodes(data_steps[0], "set_statement")
        merge_stmts = ASTBuilder.find_nodes(data_steps[0], "merge_statement")
        by_stmts = ASTBuilder.find_nodes(data_steps[0], "by_statement")
        keep_stmts = ASTBuilder.find_nodes(data_steps[0], "keep_statement")
        drop_stmts = ASTBuilder.find_nodes(data_steps[0], "drop_statement")
        length_stmts = ASTBuilder.find_nodes(data_steps[0], "length_statement")
        format_stmts = ASTBuilder.find_nodes(data_steps[0], "format_statement")
        informat_stmts = ASTBuilder.find_nodes(data_steps[0], "informat_statement")
        retain_stmts = ASTBuilder.find_nodes(data_steps[0], "retain_statement")

        # All should be found
        assert len(set_stmts) == 1
        assert len(merge_stmts) == 1
        assert len(by_stmts) == 1
        assert len(keep_stmts) == 1
        assert len(drop_stmts) == 1
        assert len(length_stmts) == 1
        assert len(format_stmts) == 1
        assert len(informat_stmts) == 1
        assert len(retain_stmts) == 1


class TestStatementAvailabilityInSemanticPass:
    """Tests verifying statements are available to semantic analysis."""

    def test_statements_available_to_semantic_analyzer(self):
        """Test that all statements are accessible to the semantic analyzer."""
        sas_code = """
        data output;
            merge left right;
            by id;
            keep id name;
            drop temp;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        # Get the data step
        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        data_step = data_steps[0]

        # Verify all children are accessible
        assert len(data_step.children) >= 4  # At least merge, by, keep, drop

        # Verify we can iterate through them
        statement_types = []
        for child in data_step.children:
            if child.node_type in [
                "merge_statement",
                "by_statement",
                "keep_statement",
                "drop_statement",
            ]:
                statement_types.append(child.node_type)

        assert "merge_statement" in statement_types
        assert "by_statement" in statement_types
        assert "keep_statement" in statement_types
        assert "drop_statement" in statement_types

    def test_statement_text_accessible_for_parsing(self):
        """Test that statement text is accessible for content extraction."""
        sas_code = """
        data output;
            merge dataset_a dataset_b dataset_c;
            by key1 key2;
            keep field1 field2 field3;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        data_step = data_steps[0]

        # Extract merge statement
        merge_stmts = ASTBuilder.find_nodes(data_step, "merge_statement")
        assert len(merge_stmts) == 1

        merge_text = merge_stmts[0].text
        assert "dataset_a" in merge_text.lower()
        assert "dataset_b" in merge_text.lower()
        assert "dataset_c" in merge_text.lower()

        # Extract by statement
        by_stmts = ASTBuilder.find_nodes(data_step, "by_statement")
        by_text = by_stmts[0].text
        assert "key1" in by_text.lower()
        assert "key2" in by_text.lower()

        # Extract keep statement
        keep_stmts = ASTBuilder.find_nodes(data_step, "keep_statement")
        keep_text = keep_stmts[0].text
        assert "field1" in keep_text.lower()
        assert "field2" in keep_text.lower()
