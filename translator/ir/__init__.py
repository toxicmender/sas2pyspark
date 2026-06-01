"""
Intermediate Representation (IR) for SAS to PySpark translation.

The IR layer abstracts SAS execution semantics and supports optimization passes
and multiple code emitters.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class JoinType(Enum):
    """Supported join types."""

    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    OUTER = "outer"


class IRNodeType(Enum):
    """Types of IR nodes."""

    DATASET = "dataset"
    FILTER = "filter"
    PROJECTION = "projection"
    ASSIGNMENT = "assignment"
    JOIN = "join"
    SORT = "sort"
    AGGREGATE = "aggregate"
    RENAME = "rename"
    UNION = "union"
    RETAIN = "retain"
    OUTPUT_SELECT = "output_select"


@dataclass
class IRNode:
    """Base class for all IR nodes."""

    node_type: IRNodeType
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(type={self.node_type.value})"


class DatasetNode(IRNode):
    """Represents a dataset source or sink."""

    def __init__(self, name: str, **metadata: Any):
        super().__init__(IRNodeType.DATASET, metadata)
        self.name = name


class FilterNode(IRNode):
    """Represents a WHERE/IF predicate."""

    def __init__(self, predicate: str, input_node: "IRNode", **metadata: Any):
        super().__init__(IRNodeType.FILTER, metadata)
        self.predicate = predicate
        self.input_node = input_node


class ProjectionNode(IRNode):
    """Represents column selection/transformation."""

    def __init__(
        self, columns: List[str], input_node: "IRNode", keep: bool = True, **metadata: Any
    ):
        super().__init__(IRNodeType.PROJECTION, metadata)
        self.columns = columns
        self.input_node = input_node
        self.keep = keep


class AssignmentNode(IRNode):
    """Represents variable/column assignment."""

    def __init__(self, column: str, expression: str, input_node: "IRNode", **metadata: Any):
        super().__init__(IRNodeType.ASSIGNMENT, metadata)
        self.column = column
        self.expression = expression
        self.input_node = input_node


class JoinNode(IRNode):
    """Represents a merge/join operation."""

    def __init__(
        self,
        left: "IRNode",
        right: "IRNode",
        keys: List[str],
        join_type: JoinType = JoinType.INNER,
        **metadata: Any,
    ):
        super().__init__(IRNodeType.JOIN, metadata)
        self.left = left
        self.right = right
        self.keys = keys
        self.join_type = join_type


class SortNode(IRNode):
    """Represents a sort/order operation."""

    def __init__(self, order_by: List[tuple[str, str]], input_node: "IRNode", **metadata: Any):
        super().__init__(IRNodeType.SORT, metadata)
        self.order_by = order_by
        self.input_node = input_node


class AggregateNode(IRNode):
    """Represents aggregation operations."""

    def __init__(
        self,
        group_by: List[str],
        aggregations: Dict[str, str],
        input_node: "IRNode",
        **metadata: Any,
    ):
        super().__init__(IRNodeType.AGGREGATE, metadata)
        self.group_by = group_by
        self.aggregations = aggregations
        self.input_node = input_node


class RenameNode(IRNode):
    """Represents column renaming."""

    def __init__(self, mapping: Dict[str, str], input_node: "IRNode", **metadata: Any):
        super().__init__(IRNodeType.RENAME, metadata)
        self.mapping = mapping
        self.input_node = input_node


class UnionNode(IRNode):
    """Represents union/concatenation of datasets."""

    def __init__(self, inputs: List["IRNode"], all_mode: bool = False, **metadata: Any):
        super().__init__(IRNodeType.UNION, metadata)
        self.inputs = inputs
        self.all_mode = all_mode


class RetainNode(IRNode):
    """Represents RETAIN statement for state preservation across iterations.

    RETAIN in SAS maintains variable values across data step iterations.
    In Spark, this is typically implemented using:
    - Window functions with lag()
    - Stateful aggregations
    - Pre-computed lag columns
    """

    def __init__(
        self,
        retain_vars: Dict[str, Optional[str]],
        input_node: "IRNode",
        **metadata: Any,
    ):
        super().__init__(IRNodeType.RETAIN, metadata)
        self.retain_vars = retain_vars  # Map of variable -> initial_value (or None)
        self.input_node = input_node


class OutputSelectNode(IRNode):
    """Represents OUTPUT statement filtering which datasets receive observations.

    OUTPUT statement in SAS controls which datasets get written.
    This node represents selective output to specific named datasets.
    """

    def __init__(
        self,
        output_datasets: List[str],
        input_node: "IRNode",
        **metadata: Any,
    ):
        super().__init__(IRNodeType.OUTPUT_SELECT, metadata)
        self.output_datasets = output_datasets
        self.input_node = input_node


@dataclass
class IRProgram:
    """Represents a complete SAS program in IR form."""

    steps: List[Union[tuple[str, IRNode]]] = field(default_factory=list)
    # List of (output_name, ir_tree) tuples

    def add_step(self, output_name: str, ir_tree: IRNode) -> None:
        """Add a translation step to the program."""
        self.steps.append((output_name, ir_tree))

    def get_steps(self) -> List[tuple[str, IRNode]]:
        """Get all steps in the program."""
        return self.steps

    def __repr__(self) -> str:
        return f"IRProgram(steps={len(self.steps)})"
