"""
Unit tests for PySpark code generation (emitters).
"""

import pytest

from translator.emitters import PySparkEmitter
from translator.ir import (
    AggregateNode,
    AssignmentNode,
    DatasetNode,
    FilterNode,
    IRProgram,
    JoinNode,
    JoinType,
    ProjectionNode,
    RenameNode,
    SortNode,
    UnionNode,
)


class TestPySparkEmitterBasics:
    """Basic tests for PySparkEmitter."""

    def test_emitter_creation(self):
        """Test creating a PySpark emitter."""
        emitter = PySparkEmitter()
        assert emitter.generated_code is not None
        assert emitter.node_counter == 0

    def test_imports_added(self):
        """Test that imports are added to generated code."""
        emitter = PySparkEmitter()
        emitter._add_imports()

        code = emitter.get_generated_code()
        assert "from pyspark.sql import functions as F" in code
        assert "from pyspark.sql.window import Window" in code


class TestDatasetNodeEmission:
    """Tests for dataset node code generation."""

    def test_emit_dataset(self):
        """Test emitting a dataset node."""
        emitter = PySparkEmitter()
        dataset_node = DatasetNode("my_table")

        var_name = emitter.emit_node(dataset_node)

        code = emitter.get_generated_code()
        assert 'spark.table("my_table")' in code
        assert var_name.startswith("df_")


class TestFilterNodeEmission:
    """Tests for filter node code generation."""

    def test_emit_filter(self):
        """Test emitting a filter node."""
        emitter = PySparkEmitter()
        input_node = DatasetNode("input")
        filter_node = FilterNode("F.col('age') > 18", input_node)

        var_name = emitter.emit_node(filter_node)

        code = emitter.get_generated_code()
        assert ".filter(" in code
        assert "F.col('age') > 18" in code


class TestProjectionNodeEmission:
    """Tests for projection node code generation."""

    def test_emit_projection_keep(self):
        """Test emitting projection with KEEP."""
        emitter = PySparkEmitter()
        input_node = DatasetNode("input")
        proj_node = ProjectionNode(["col1", "col2"], input_node, keep=True)

        var_name = emitter.emit_node(proj_node)

        code = emitter.get_generated_code()
        assert ".select(" in code
        assert '"col1"' in code
        assert '"col2"' in code

    def test_emit_projection_drop(self):
        """Test emitting projection with DROP."""
        emitter = PySparkEmitter()
        input_node = DatasetNode("input")
        proj_node = ProjectionNode(["col3"], input_node, keep=False)

        var_name = emitter.emit_node(proj_node)

        code = emitter.get_generated_code()
        assert ".drop(" in code
        assert '"col3"' in code


class TestAssignmentNodeEmission:
    """Tests for assignment node code generation."""

    def test_emit_assignment(self):
        """Test emitting an assignment node."""
        emitter = PySparkEmitter()
        input_node = DatasetNode("input")
        assign_node = AssignmentNode("total", "F.col('a') + F.col('b')", input_node)

        var_name = emitter.emit_node(assign_node)

        code = emitter.get_generated_code()
        assert '.withColumn("total"' in code
        assert "F.col('a') + F.col('b')" in code


class TestJoinNodeEmission:
    """Tests for join node code generation."""

    def test_emit_inner_join(self):
        """Test emitting an inner join."""
        emitter = PySparkEmitter()
        left = DatasetNode("left_table")
        right = DatasetNode("right_table")
        join_node = JoinNode(left, right, ["id"], JoinType.INNER)

        var_name = emitter.emit_node(join_node)

        code = emitter.get_generated_code()
        assert ".join(" in code
        assert 'how="inner"' in code
        assert '"id"' in code

    def test_emit_left_join(self):
        """Test emitting a left join."""
        emitter = PySparkEmitter()
        left = DatasetNode("left_table")
        right = DatasetNode("right_table")
        join_node = JoinNode(left, right, ["id"], JoinType.LEFT)

        var_name = emitter.emit_node(join_node)

        code = emitter.get_generated_code()
        assert 'how="left"' in code

    def test_emit_join_multiple_keys(self):
        """Test emitting a join with multiple keys."""
        emitter = PySparkEmitter()
        left = DatasetNode("left")
        right = DatasetNode("right")
        join_node = JoinNode(left, right, ["id", "date"])

        var_name = emitter.emit_node(join_node)

        code = emitter.get_generated_code()
        assert '"id"' in code
        assert '"date"' in code


class TestSortNodeEmission:
    """Tests for sort node code generation."""

    def test_emit_sort(self):
        """Test emitting a sort node."""
        emitter = PySparkEmitter()
        input_node = DatasetNode("input")
        sort_node = SortNode([("col1", "asc"), ("col2", "desc")], input_node)

        var_name = emitter.emit_node(sort_node)

        code = emitter.get_generated_code()
        assert ".orderBy(" in code
        assert ".asc()" in code
        assert ".desc()" in code


class TestAggregateNodeEmission:
    """Tests for aggregate node code generation."""

    def test_emit_aggregate(self):
        """Test emitting an aggregate node."""
        emitter = PySparkEmitter()
        input_node = DatasetNode("input")
        agg_node = AggregateNode(
            ["category"],
            {"revenue": "sum", "count": "count"},
            input_node,
        )

        var_name = emitter.emit_node(agg_node)

        code = emitter.get_generated_code()
        assert ".groupBy(" in code
        assert "F.sum(" in code
        assert "F.count(" in code


class TestRenameNodeEmission:
    """Tests for rename node code generation."""

    def test_emit_rename(self):
        """Test emitting a rename node."""
        emitter = PySparkEmitter()
        input_node = DatasetNode("input")
        rename_node = RenameNode({"old_col": "new_col"}, input_node)

        var_name = emitter.emit_node(rename_node)

        code = emitter.get_generated_code()
        assert ".withColumnRenamed(" in code
        assert '"old_col"' in code
        assert '"new_col"' in code


class TestUnionNodeEmission:
    """Tests for union node code generation."""

    def test_emit_union(self):
        """Test emitting a union node."""
        emitter = PySparkEmitter()
        input1 = DatasetNode("table1")
        input2 = DatasetNode("table2")
        union_node = UnionNode([input1, input2])

        var_name = emitter.emit_node(union_node)

        code = emitter.get_generated_code()
        assert "unionByName" in code


class TestProgramEmission:
    """Tests for full program emission."""

    def test_emit_empty_program(self):
        """Test emitting an empty program."""
        emitter = PySparkEmitter()
        program = IRProgram()

        code = emitter.emit_program(program)

        assert "from pyspark.sql import functions as F" in code

    def test_emit_single_step_program(self):
        """Test emitting a program with one step."""
        emitter = PySparkEmitter()
        program = IRProgram()

        dataset_node = DatasetNode("input_table")
        program.add_step("output_table", dataset_node)

        code = emitter.emit_program(program)

        assert 'spark.table("input_table")' in code
        assert 'saveAsTable("output_table")' in code

    def test_emit_multi_step_program(self):
        """Test emitting a program with multiple steps."""
        emitter = PySparkEmitter()
        program = IRProgram()

        step1_input = DatasetNode("raw_data")
        program.add_step("temp1", step1_input)

        step2_input = DatasetNode("temp1")
        program.add_step("final_output", step2_input)

        code = emitter.emit_program(program)

        assert 'spark.table("raw_data")' in code
        assert 'spark.table("temp1")' in code
        assert 'saveAsTable("temp1")' in code
        assert 'saveAsTable("final_output")' in code


class TestComplexPipeline:
    """Tests for complex translation pipelines."""

    def test_filter_and_projection_pipeline(self):
        """Test a pipeline with filtering and projection."""
        emitter = PySparkEmitter()

        # Create pipeline: load -> filter -> select
        dataset = DatasetNode("raw_data")
        filtered = FilterNode("F.col('active') == True", dataset)
        projected = ProjectionNode(["id", "name"], filtered, keep=True)

        var_name = emitter.emit_node(projected)

        code = emitter.get_generated_code()
        assert 'spark.table("raw_data")' in code
        assert ".filter(" in code
        assert ".select(" in code

    def test_join_and_aggregate_pipeline(self):
        """Test a pipeline with join and aggregation."""
        emitter = PySparkEmitter()

        # Create pipeline: join -> aggregate
        left = DatasetNode("customers")
        right = DatasetNode("orders")
        joined = JoinNode(left, right, ["customer_id"])
        aggregated = AggregateNode(
            ["customer_id"],
            {"order_total": "sum"},
            joined,
        )

        var_name = emitter.emit_node(aggregated)

        code = emitter.get_generated_code()
        assert ".join(" in code
        assert ".groupBy(" in code
