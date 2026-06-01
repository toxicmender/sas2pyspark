"""Tests for RETAIN and OUTPUT statement IR lowering.

This module demonstrates that RETAIN and OUTPUT statements are now properly
lowered to IR nodes (RetainNode and OutputSelectNode) rather than being
warnings-only or skipped.
"""

import pytest

from translator.ir import IRNodeType, OutputSelectNode, RetainNode
from translator.parser import ASTBuilder, SASParser
from translator.semantic.lower import DataStepLowerer


class TestRetainStatementIRLowering:
    """Tests that RETAIN statements are properly lowered to IR."""

    def test_retain_single_variable(self):
        """Test RETAIN with a single variable creates RetainNode in IR."""
        sas_code = """
        data output;
            set input;
            retain counter 0;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        # Should have RetainNode in the IR tree
        assert ir_node is not None
        # Traverse to find RetainNode
        current = ir_node
        found = False
        while current:
            if isinstance(current, RetainNode):
                found = True
                break
            current = getattr(current, "input_node", None)
        assert found, "RetainNode should be in IR tree"

    def test_retain_multiple_variables(self):
        """Test RETAIN with multiple variables."""
        sas_code = """
        data output;
            set input;
            retain counter 0 running_total 0;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert ir_node is not None
        # Verify variables are tracked in lowerer
        assert "counter" in lowerer.retain_vars
        assert "running_total" in lowerer.retain_vars

    def test_retain_with_initial_values(self):
        """Test RETAIN extracts initial values correctly."""
        sas_code = """
        data output;
            set input;
            retain x 10 y 20.5 z 0;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert ir_node is not None
        # Verify initial values are captured
        assert lowerer.retain_vars.get("x") == "10"
        assert lowerer.retain_vars.get("y") == "20.5"
        assert lowerer.retain_vars.get("z") == "0"


class TestOutputStatementIRLowering:
    """Tests that OUTPUT statements are properly lowered to IR."""

    def test_output_select_node_creation(self):
        """Test that OutputSelectNode is created when OUTPUT is specified."""
        sas_code = """
        data output;
            set input;
            output output_dataset;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        # OutputSelectNode should be top-level when OUTPUT is explicitly used
        assert isinstance(ir_node, OutputSelectNode)
        assert ir_node.output_datasets == ["output_dataset"]
        assert ir_node.node_type == IRNodeType.OUTPUT_SELECT

    def test_output_tracks_datasets(self):
        """Test OUTPUT statement properly tracks output datasets."""
        sas_code = """
        data output;
            set input;
            output ds1 ds2;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert ir_node is not None
        assert "ds1" in lowerer.output_datasets or "ds2" in lowerer.output_datasets


class TestRetainAndOutputCombinations:
    """Tests for DATA steps with both RETAIN and OUTPUT statements."""

    def test_retain_and_output_together(self):
        """Test DATA step with both RETAIN and OUTPUT generates proper IR."""
        sas_code = """
        data output;
            set input;
            retain counter 0;
            counter + 1;
            if counter > 5 then output;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert ir_node is not None
        # Both RETAIN and OUTPUT should be tracked
        assert "counter" in lowerer.retain_vars
        assert lowerer.output_datasets  # OUTPUT was processed


class TestIRNodeTypes:
    """Tests that verify IR node types are properly set."""

    def test_retain_node_type_is_correct(self):
        """Verify RetainNode has correct IRNodeType."""
        sas_code = """
        data output;
            set input;
            retain counter 0;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        # Find RetainNode
        current = ir_node
        while current:
            if isinstance(current, RetainNode):
                assert current.node_type == IRNodeType.RETAIN
                assert hasattr(current, "retain_vars")
                assert hasattr(current, "input_node")
                return
            current = getattr(current, "input_node", None)

        raise AssertionError("RetainNode not found in IR tree")

    def test_output_node_type_is_correct(self):
        """Verify OutputSelectNode has correct IRNodeType."""
        sas_code = """
        data output;
            set input;
            output target_dataset;
        run;
        """
        parser = SASParser()
        ast_dict = parser.parse(sas_code)
        ast_root = ASTBuilder.build_from_dict(ast_dict)

        data_steps = ASTBuilder.find_nodes(ast_root, "data_step")
        lowerer = DataStepLowerer()

        ir_node = lowerer.lower_data_step(data_steps[0], "output")

        assert isinstance(ir_node, OutputSelectNode)
        assert ir_node.node_type == IRNodeType.OUTPUT_SELECT
        assert hasattr(ir_node, "output_datasets")
        assert hasattr(ir_node, "input_node")
