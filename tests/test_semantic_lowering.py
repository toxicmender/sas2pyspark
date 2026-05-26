"""
Unit tests for semantic lowering (AST to IR conversion).

Tests the ability to lower DATA steps with multiple datasets and multiple steps.
"""

import pytest

from translator.ir import DatasetNode, IRProgram, JoinNode, ProjectionNode, UnionNode
from translator.parser import ASTBuilder, SASParser
from translator.semantic.lower import DataStepLowerer, SASLowerer


class TestDataStepLowering:
    """Tests for lowering individual DATA steps to IR."""

    def test_lower_single_set_dataset(self):
        """Test lowering DATA step with single SET dataset."""
        sas_code = """
        data output;
            set input;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        # Get the data step node
        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        assert len(data_steps) == 1

        # Lower it
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert ir_node is not None
        assert ir_node.node_type.value == "dataset"

    def test_lower_multiple_set_datasets(self):
        """Test lowering DATA step with multiple SET datasets."""
        sas_code = """
        data output;
            set input1 input2 input3;
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
        # Multiple datasets should produce a UNION node
        assert ir_node.node_type.value == "union"

    def test_lower_merge_datasets(self):
        """Test lowering DATA step with MERGE statement."""
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
        assert len(data_steps) == 1

        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert ir_node is not None
        # Should eventually produce a JOIN or SORT node
        assert ir_node.node_type.value in ["join", "sort"]

    def test_lower_merge_multiple_datasets(self):
        """Test lowering DATA step with MERGE of 3+ datasets."""
        sas_code = """
        data output;
            merge ds1 ds2 ds3 ds4;
            by key;
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
        # Multiple merges should produce a JOIN tree
        # The top node should be SORT (from BY) or JOIN

    def test_lower_with_keep_statement(self):
        """Test lowering DATA step with KEEP statement."""
        sas_code = """
        data output;
            set input;
            keep var1 var2 var3;
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
        # Should have a PROJECTION node
        assert ir_node.node_type.value == "projection"

    def test_lower_with_drop_statement(self):
        """Test lowering DATA step with DROP statement."""
        sas_code = """
        data output;
            set input;
            drop unwanted_var;
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
        assert ir_node.node_type.value == "projection"

    def test_lower_with_assignment(self):
        """Test lowering DATA step with column assignment."""
        sas_code = """
        data output;
            set input;
            new_var = existing_var * 2;
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
        # Should have an ASSIGNMENT node
        assert ir_node.node_type.value == "assignment"

    def test_lower_complex_data_step(self):
        """Test lowering complex DATA step with multiple statement types."""
        sas_code = """
        data output;
            merge left right;
            by id;
            keep id name value;
            drop tax_code;
            total = value * quantity;
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
        # Should have nested nodes
        assert ir_node.node_type is not None


class TestMultipleDataSteps:
    """Tests for handling multiple DATA steps in a program."""

    def test_lower_two_data_steps(self):
        """Test lowering program with two DATA steps."""
        sas_code = """
        data step1;
            set input;
            keep var1;
        run;

        data step2;
            set step1;
            total = var1 * 2;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        lowerer = SASLowerer()
        ir_program = lowerer.lower_program(ast_root)

        # Should have two steps in the IR program
        assert len(ir_program.get_steps()) == 2

    def test_lower_multiple_data_steps_with_dependencies(self):
        """Test lowering multiple DATA steps where later steps depend on earlier ones."""
        sas_code = """
        data temp1;
            set raw_data;
            keep id value;
        run;

        data temp2;
            set temp1;
            where value > 100;
        run;

        data final;
            set temp2;
            status = 'PROCESSED';
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        lowerer = SASLowerer()
        ir_program = lowerer.lower_program(ast_root)

        # Should have three steps
        steps = ir_program.get_steps()
        assert len(steps) == 3

        # Check that each step has correct output names
        assert steps[0][0] == "temp1"
        assert steps[1][0] == "temp2"
        assert steps[2][0] == "final"

    def test_lower_multiple_data_steps_parallel(self):
        """Test lowering multiple DATA steps that don't depend on each other."""
        sas_code = """
        data out1;
            set in1;
        run;

        data out2;
            set in2;
        run;

        data out3;
            set in3;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        lowerer = SASLowerer()
        ir_program = lowerer.lower_program(ast_root)

        # Should have three independent steps
        steps = ir_program.get_steps()
        assert len(steps) == 3
        assert steps[0][0] == "out1"
        assert steps[1][0] == "out2"
        assert steps[2][0] == "out3"


class TestMultipleDatasetHandling:
    """Tests for proper handling of multiple datasets in SET/MERGE."""

    def test_set_two_datasets(self):
        """Test SET statement with two datasets produces UNION."""
        sas_code = """
        data combined;
            set data1 data2;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "combined")

        assert ir_node is not None
        assert ir_node.node_type.value == "union"

    def test_set_three_datasets(self):
        """Test SET statement with three datasets."""
        sas_code = """
        data combined;
            set d1 d2 d3;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "combined")

        assert ir_node is not None
        assert ir_node.node_type.value == "union"

    def test_merge_two_datasets(self):
        """Test MERGE statement with two datasets."""
        sas_code = """
        data merged;
            merge left right;
            by key;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "merged")

        assert ir_node is not None
        # Should be SORT node (containing JOIN node with BY keys)

    def test_merge_three_datasets(self):
        """Test MERGE statement with three datasets creates JOIN tree."""
        sas_code = """
        data merged;
            merge d1 d2 d3;
            by key;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "merged")

        assert ir_node is not None
        # Multiple merges create nested JOIN nodes

    def test_set_with_keep_multiple_inputs(self):
        """Test SET with multiple datasets and KEEP statement."""
        sas_code = """
        data combined;
            set in1 in2 in3;
            keep id value date;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "combined")

        assert ir_node is not None
        # Should have PROJECTION wrapping UNION
        assert ir_node.node_type.value == "projection"


class TestIRCorrectness:
    """Tests for correctness of generated IR."""

    def test_ir_program_contains_all_steps(self):
        """Test that IR program contains IR for all DATA steps."""
        sas_code = """
        data step1; set in1; run;
        data step2; set in2; run;
        data step3; set in3; run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        lowerer = SASLowerer()
        ir_program = lowerer.lower_program(ast_root)

        # All steps should be present
        assert len(ir_program.get_steps()) == 3

    def test_ir_preserves_dataset_names(self):
        """Test that output dataset names are preserved in IR."""
        sas_code = """
        data final_output;
            set raw_input;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        lowerer = SASLowerer()
        ir_program = lowerer.lower_program(ast_root)

        steps = ir_program.get_steps()
        assert len(steps) == 1
        assert steps[0][0] == "final_output"

    def test_union_node_has_all_datasets(self):
        """Test that UNION node contains all input datasets."""
        sas_code = """
        data combined;
            set ds1 ds2 ds3;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "combined")

        assert isinstance(ir_node, UnionNode)
        # Should have 3 input nodes
        assert len(ir_node.inputs) == 3


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_data_step(self):
        """Test lowering empty DATA step."""
        sas_code = "data output; run;"
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        # Should create a NULL dataset node
        assert ir_node is not None
        assert ir_node.node_type.value == "dataset"

    def test_multiple_output_datasets(self):
        """Test DATA step creating multiple output datasets."""
        sas_code = """
        data out1 out2;
            set input;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        lowerer = SASLowerer()
        ir_program = lowerer.lower_program(ast_root)

        # Should create IR for both output datasets
        steps = ir_program.get_steps()
        assert len(steps) == 2
        assert steps[0][0] == "out1"
        assert steps[1][0] == "out2"

    def test_set_with_comma_separated_datasets(self):
        """Test SET statement with comma-separated datasets."""
        sas_code = """
        data combined;
            set data1, data2, data3;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()
        ir_node = lowerer.lower_data_step(data_steps[0], "combined")

        # Should handle comma-separated datasets
        assert ir_node is not None
        assert ir_node.node_type.value == "union"
