"""
Code generation layer for PySpark emission.

Responsible for converting IR nodes into PySpark DataFrame API calls.
"""

from typing import Dict, List, Optional

from translator.ir import (
    AggregateNode,
    AssignmentNode,
    DatasetNode,
    FilterNode,
    IRNode,
    IRNodeType,
    IRProgram,
    JoinNode,
    JoinType,
    ProjectionNode,
    RenameNode,
    SortNode,
    UnionNode,
)


class PySparkEmitter:
    """Emits PySpark code from IR nodes."""

    def __init__(self):
        self.generated_code: List[str] = []
        self.imports_added = False
        self.node_counter = 0

    def _add_imports(self) -> None:
        """Add necessary imports."""
        if not self.imports_added:
            self.generated_code.extend(
                [
                    "from pyspark.sql import functions as F",
                    "from pyspark.sql.window import Window",
                    "from pyspark.sql.types import *",
                    "",
                ]
            )
            self.imports_added = True

    def _get_var_name(self, base: str = "df") -> str:
        """Generate unique variable name."""
        self.node_counter += 1
        return f"{base}_{self.node_counter}"

    def emit_node(self, node: IRNode, input_var: str = "df") -> str:
        """Emit code for a single IR node and return the output variable name."""
        if not self.imports_added:
            self._add_imports()

        if node.node_type == IRNodeType.DATASET:
            return self._emit_dataset(node, input_var)
        elif node.node_type == IRNodeType.FILTER:
            return self._emit_filter(node, input_var)
        elif node.node_type == IRNodeType.PROJECTION:
            return self._emit_projection(node, input_var)
        elif node.node_type == IRNodeType.ASSIGNMENT:
            return self._emit_assignment(node, input_var)
        elif node.node_type == IRNodeType.JOIN:
            return self._emit_join(node, input_var)
        elif node.node_type == IRNodeType.SORT:
            return self._emit_sort(node, input_var)
        elif node.node_type == IRNodeType.AGGREGATE:
            return self._emit_aggregate(node, input_var)
        elif node.node_type == IRNodeType.RENAME:
            return self._emit_rename(node, input_var)
        elif node.node_type == IRNodeType.UNION:
            return self._emit_union(node, input_var)
        else:
            raise ValueError(f"Unknown node type: {node.node_type}")

    def _emit_dataset(self, node: DatasetNode, input_var: str) -> str:
        """Emit code for loading a dataset."""
        var_name = self._get_var_name()
        self.generated_code.append(f'{var_name} = spark.table("{node.name}")')
        return var_name

    def _emit_filter(self, node: FilterNode, input_var: str) -> str:
        """Emit code for filtering."""
        input_var = self.emit_node(node.input_node, input_var)
        var_name = self._get_var_name()
        self.generated_code.append(f"{var_name} = {input_var}.filter({node.predicate})")
        return var_name

    def _emit_projection(self, node: ProjectionNode, input_var: str) -> str:
        """Emit code for column selection."""
        input_var = self.emit_node(node.input_node, input_var)
        var_name = self._get_var_name()
        columns_str = ", ".join(f'"{col}"' for col in node.columns)
        if node.keep:
            self.generated_code.append(f"{var_name} = {input_var}.select({columns_str})")
        else:
            self.generated_code.append(f"{var_name} = {input_var}.drop({columns_str})")
        return var_name

    def _emit_assignment(self, node: AssignmentNode, input_var: str) -> str:
        """Emit code for column assignment."""
        input_var = self.emit_node(node.input_node, input_var)
        var_name = self._get_var_name()
        self.generated_code.append(
            f'{var_name} = {input_var}.withColumn("{node.column}", {node.expression})'
        )
        return var_name

    def _emit_join(self, node: JoinNode, input_var: str) -> str:
        """Emit code for join operation."""
        left_var = self.emit_node(node.left, input_var)
        right_var = self.emit_node(node.right, input_var)
        var_name = self._get_var_name()
        keys_str = ", ".join(f'"{key}"' for key in node.keys)
        join_type = node.join_type.value
        self.generated_code.append(
            f'{var_name} = {left_var}.join({right_var}, on=[{keys_str}], how="{join_type}")'
        )
        return var_name

    def _emit_sort(self, node: SortNode, input_var: str) -> str:
        """Emit code for sorting."""
        input_var = self.emit_node(node.input_node, input_var)
        var_name = self._get_var_name()

        sort_cols = []
        for col, direction in node.order_by:
            if direction.lower() == "desc":
                sort_cols.append(f'F.col("{col}").desc()')
            else:
                sort_cols.append(f'F.col("{col}").asc()')

        cols_str = ", ".join(sort_cols)
        self.generated_code.append(f"{var_name} = {input_var}.orderBy({cols_str})")
        return var_name

    def _emit_aggregate(self, node: AggregateNode, input_var: str) -> str:
        """Emit code for aggregation."""
        input_var = self.emit_node(node.input_node, input_var)
        var_name = self._get_var_name()

        group_by_cols = ", ".join(f'"{col}"' for col in node.group_by)
        agg_specs = []
        for col, agg_func in node.aggregations.items():
            agg_specs.append(f'F.{agg_func}("{col}").alias("{col}_{agg_func}")')

        agg_str = ", ".join(agg_specs)
        self.generated_code.append(
            f"{var_name} = {input_var}.groupBy({group_by_cols}).agg({agg_str})"
        )
        return var_name

    def _emit_rename(self, node: RenameNode, input_var: str) -> str:
        """Emit code for column renaming."""
        input_var = self.emit_node(node.input_node, input_var)
        var_name = input_var

        for old_name, new_name in node.mapping.items():
            var_name = self._get_var_name()
            self.generated_code.append(
                f'{var_name} = {input_var}.withColumnRenamed("{old_name}", "{new_name}")'
            )
            input_var = var_name

        return var_name

    def _emit_union(self, node: UnionNode, input_var: str) -> str:
        """Emit code for union operation."""
        input_vars = []
        for input_node in node.inputs:
            input_vars.append(self.emit_node(input_node, input_var))

        var_name = self._get_var_name()
        union_method = "unionByName" if not node.all_mode else "unionByName"

        inputs_str = ", ".join(input_vars)
        self.generated_code.append(
            f"{var_name} = {input_vars[0]}.{union_method}([{', '.join(input_vars[1:])}])"
        )
        return var_name

    def emit_program(self, program: IRProgram) -> str:
        """Emit complete PySpark program from IR program."""
        self.generated_code = []
        self.node_counter = 0
        self._add_imports()

        for output_name, ir_tree in program.get_steps():
            var_name = self.emit_node(ir_tree)
            self.generated_code.append(
                f'{var_name}.write.mode("overwrite").saveAsTable("{output_name}")'
            )
            self.generated_code.append("")

        return "\n".join(self.generated_code)

    def get_generated_code(self) -> str:
        """Get all generated code as a string."""
        return "\n".join(self.generated_code)
