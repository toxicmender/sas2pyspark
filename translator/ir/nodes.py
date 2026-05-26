from __future__ import annotations

from dataclasses import dataclass

from ..ast import Expression
from ..diagnostics import Diagnostic


class IRNode:
    pass


@dataclass(frozen=True)
class DatasetNode(IRNode):
    name: str


@dataclass(frozen=True)
class FilterNode(IRNode):
    predicate: Expression


@dataclass(frozen=True)
class AssignmentNode(IRNode):
    column: str
    expression: Expression


@dataclass(frozen=True)
class UnionNode(IRNode):
    dataset: str


@dataclass(frozen=True)
class JoinNode(IRNode):
    dataset: str
    keys: list[str]
    join_type: str


@dataclass(frozen=True)
class KeepNode(IRNode):
    columns: list[str]


@dataclass(frozen=True)
class DropNode(IRNode):
    columns: list[str]


@dataclass(frozen=True)
class WriteNode(IRNode):
    target: str


@dataclass(frozen=True)
class ConditionalWriteNode(IRNode):
    target: str
    predicate: Expression


@dataclass
class IRPlan:
    source: DatasetNode
    transforms: list[IRNode]
    target: str
    diagnostics: list[Diagnostic]
