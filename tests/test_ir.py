"""
Unit tests for the IR (Intermediate Representation) module.
"""

import pytest

from translator.ir import (
    AggregateNode,
    AssignmentNode,
    DatasetNode,
    FilterNode,
    IRNodeType,
    IRProgram,
    JoinNode,
    JoinType,
    ProjectionNode,
    RenameNode,
    SortNode,
    UnionNode,
)


class TestDatasetNode:
    """Tests for DatasetNode."""

    def test_dataset_node_creation(self):
        """Test basic dataset node creation."""
        node = DatasetNode("my_dataset")
        assert node.name == "my_dataset"
        assert node.node_type == IRNodeType.DATASET

    def test_dataset_node_with_metadata(self):
        """Test dataset node with metadata."""
        node = DatasetNode("my_dataset", source="source_table", obs_count=1000)
        assert node.name == "my_dataset"
        assert node.metadata["source"] == "source_table"
        assert node.metadata["obs_count"] == 1000


class TestFilterNode:
    """Tests for FilterNode."""

    def test_filter_node_creation(self):
        """Test filter node creation."""
        input_node = DatasetNode("input_data")
        filter_node = FilterNode("age > 18", input_node)
        assert filter_node.predicate == "age > 18"
        assert filter_node.input_node == input_node
        assert filter_node.node_type == IRNodeType.FILTER

    def test_filter_node_nesting(self):
        """Test nested filter nodes."""
        node1 = DatasetNode("input")
        node2 = FilterNode("age > 18", node1)
        node3 = FilterNode("income > 50000", node2)

        assert node3.input_node == node2
        assert node2.input_node == node1


class TestProjectionNode:
    """Tests for ProjectionNode."""

    def test_projection_keep(self):
        """Test projection with KEEP."""
        input_node = DatasetNode("input")
        proj_node = ProjectionNode(["col1", "col2"], input_node, keep=True)

        assert proj_node.columns == ["col1", "col2"]
        assert proj_node.keep is True

    def test_projection_drop(self):
        """Test projection with DROP."""
        input_node = DatasetNode("input")
        proj_node = ProjectionNode(["col3", "col4"], input_node, keep=False)

        assert proj_node.columns == ["col3", "col4"]
        assert proj_node.keep is False


class TestAssignmentNode:
    """Tests for AssignmentNode."""

    def test_assignment_creation(self):
        """Test assignment node creation."""
        input_node = DatasetNode("input")
        assign_node = AssignmentNode("new_col", "F.col('a') + F.col('b')", input_node)

        assert assign_node.column == "new_col"
        assert assign_node.expression == "F.col('a') + F.col('b')"
        assert assign_node.input_node == input_node


class TestJoinNode:
    """Tests for JoinNode."""

    def test_inner_join(self):
        """Test inner join node."""
        left = DatasetNode("left_table")
        right = DatasetNode("right_table")
        join_node = JoinNode(left, right, ["id"], JoinType.INNER)

        assert join_node.left == left
        assert join_node.right == right
        assert join_node.keys == ["id"]
        assert join_node.join_type == JoinType.INNER

    def test_left_join(self):
        """Test left join node."""
        left = DatasetNode("left_table")
        right = DatasetNode("right_table")
        join_node = JoinNode(left, right, ["id"], JoinType.LEFT)

        assert join_node.join_type == JoinType.LEFT

    def test_join_multiple_keys(self):
        """Test join with multiple keys."""
        left = DatasetNode("left")
        right = DatasetNode("right")
        join_node = JoinNode(left, right, ["id", "date"])

        assert join_node.keys == ["id", "date"]


class TestSortNode:
    """Tests for SortNode."""

    def test_sort_ascending(self):
        """Test sort in ascending order."""
        input_node = DatasetNode("input")
        sort_node = SortNode([("col1", "asc"), ("col2", "desc")], input_node)

        assert sort_node.order_by == [("col1", "asc"), ("col2", "desc")]


class TestAggregateNode:
    """Tests for AggregateNode."""

    def test_aggregate_creation(self):
        """Test aggregate node creation."""
        input_node = DatasetNode("input")
        agg_node = AggregateNode(["category"], {"revenue": "sum", "count": "count"}, input_node)

        assert agg_node.group_by == ["category"]
        assert agg_node.aggregations == {"revenue": "sum", "count": "count"}


class TestRenameNode:
    """Tests for RenameNode."""

    def test_rename_single_column(self):
        """Test renaming a single column."""
        input_node = DatasetNode("input")
        rename_node = RenameNode({"old_name": "new_name"}, input_node)

        assert rename_node.mapping == {"old_name": "new_name"}


class TestUnionNode:
    """Tests for UnionNode."""

    def test_union_creation(self):
        """Test union node creation."""
        input1 = DatasetNode("table1")
        input2 = DatasetNode("table2")
        union_node = UnionNode([input1, input2], all_mode=False)

        assert len(union_node.inputs) == 2
        assert union_node.all_mode is False


class TestIRProgram:
    """Tests for IRProgram."""

    def test_program_creation(self):
        """Test IR program creation."""
        program = IRProgram()
        assert len(program.get_steps()) == 0

    def test_add_step(self):
        """Test adding steps to a program."""
        program = IRProgram()
        node = DatasetNode("test_data")

        program.add_step("output1", node)

        steps = program.get_steps()
        assert len(steps) == 1
        assert steps[0][0] == "output1"
        assert steps[0][1] == node

    def test_multiple_steps(self):
        """Test adding multiple steps."""
        program = IRProgram()
        node1 = DatasetNode("input1")
        node2 = DatasetNode("input2")

        program.add_step("output1", node1)
        program.add_step("output2", node2)

        steps = program.get_steps()
        assert len(steps) == 2
        assert steps[0][0] == "output1"
        assert steps[1][0] == "output2"

    def test_program_repr(self):
        """Test program string representation."""
        program = IRProgram()
        program.add_step("test", DatasetNode("data"))

        repr_str = repr(program)
        assert "IRProgram" in repr_str
        assert "steps=1" in repr_str
