"""
SAS to PySpark Translator Framework.

A compiler-style framework for translating SAS programs into PySpark code
using tree-sitter for syntactic parsing and semantic analysis.
"""

__version__ = "0.1.0"
__author__ = "Author"

from translator.emitters import PySparkEmitter
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
from translator.parser import ASTBuilder, ASTNode, SASParser
from translator.semantic import (
    DatasetMetadata,
    SemanticAnalyzer,
    SemanticContext,
    Variable,
    VariableScope,
    VariableType,
)

__all__ = [
    "PySparkEmitter",
    "AggregateNode",
    "AssignmentNode",
    "DatasetNode",
    "FilterNode",
    "IRNodeType",
    "IRProgram",
    "JoinNode",
    "JoinType",
    "ProjectionNode",
    "RenameNode",
    "SortNode",
    "UnionNode",
    "ASTBuilder",
    "ASTNode",
    "SASParser",
    "DatasetMetadata",
    "SemanticAnalyzer",
    "SemanticContext",
    "Variable",
    "VariableScope",
    "VariableType",
]
