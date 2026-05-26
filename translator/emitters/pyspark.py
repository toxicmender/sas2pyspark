from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ast import (
    BinaryOp,
    CaseWhen,
    Expression,
    FunctionCall,
    Identifier,
    NumberLiteral,
    RawExpression,
    StringLiteral,
    UnaryOp,
)
from ..ir.nodes import (
    AssignmentNode,
    ConditionalWriteNode,
    DropNode,
    FilterNode,
    IRPlan,
    JoinNode,
    KeepNode,
    UnionNode,
    WriteNode,
)

DEFAULT_FUNCTION_MAP = {
    "substr": "substring",
    "upcase": "upper",
    "lowcase": "lower",
    "trim": "trim",
    "compress": "regexp_replace",
    "scan": "split",
    "today": "current_date",
    "datepart": "to_date",
    "year": "year",
    "month": "month",
    "day": "day",
    "sum": "sum",
    "mean": "avg",
    "n": "count",
}


@dataclass
class PySparkEmitter:
    function_map: dict[str, str]

    @classmethod
    def with_default_map(cls) -> "PySparkEmitter":
        return cls(load_function_map())

    def emit(self, plan: IRPlan) -> str:
        return self.emit_program([plan])

    def emit_program(self, plans: list[IRPlan]) -> str:
        if not plans:
            return ""
        lines = [
            "from pyspark.sql import functions as F",
            "from pyspark.sql.window import Window",
            "",
        ]
        for index, plan in enumerate(plans):
            if index > 0:
                lines.append("")
            lines.extend(self.emit_plan(plan))
        return "\n".join(lines)

    def emit_plan(self, plan: IRPlan) -> list[str]:
        lines = [f'df = spark.table("{plan.source.name}")']

        for transform in plan.transforms:
            if isinstance(transform, AssignmentNode):
                expr = emit_expression(transform.expression, self.function_map)
                lines.append(f'df = df.withColumn("{transform.column}", {expr})')
                continue
            if isinstance(transform, FilterNode):
                predicate = emit_expression(transform.predicate, self.function_map)
                lines.append(f"df = df.filter({predicate})")
                continue
            if isinstance(transform, UnionNode):
                lines.append(
                    f'df = df.unionByName(spark.table("{transform.dataset}"), allowMissingColumns=True)'
                )
                continue
            if isinstance(transform, JoinNode):
                keys = ", ".join(f'"{key}"' for key in transform.keys)
                lines.append(
                    f'df = df.join(spark.table("{transform.dataset}"), on=[{keys}], how="{transform.join_type}")'
                )
                continue
            if isinstance(transform, KeepNode):
                columns = ", ".join(f'"{col}"' for col in transform.columns)
                lines.append(f"df = df.select({columns})")
                continue
            if isinstance(transform, DropNode):
                columns = ", ".join(f'"{col}"' for col in transform.columns)
                lines.append(f"df = df.drop({columns})")
                continue
            if isinstance(transform, ConditionalWriteNode):
                predicate = emit_expression(transform.predicate, self.function_map)
                lines.append(
                    f'df.filter({predicate}).write.saveAsTable("{transform.target}")'
                )
                continue
            if isinstance(transform, WriteNode):
                lines.append(f'df.write.saveAsTable("{transform.target}")')
                continue
            raise ValueError(f"Unsupported IR node: {transform}")

        if plan.target:
            lines.append(f'df.write.saveAsTable("{plan.target}")')
        return lines


def load_function_map() -> dict[str, str]:
    mapping_path = (
        Path(__file__).resolve().parents[1] / "mappings" / "function_map.yaml"
    )
    try:
        import yaml

        if mapping_path.exists():
            data = yaml.safe_load(mapping_path.read_text(encoding="utf-8")) or {}
            return {str(key).lower(): str(value) for key, value in data.items()}
    except ModuleNotFoundError:
        pass
    return DEFAULT_FUNCTION_MAP.copy()


def emit_expression(expr: Expression, function_map: dict[str, str]) -> str:
    if isinstance(expr, Identifier):
        return f'F.col("{expr.name}")'
    if isinstance(expr, NumberLiteral):
        return f"F.lit({expr.value})"
    if isinstance(expr, StringLiteral):
        return f'F.lit("{escape_string(expr.value)}")'
    if isinstance(expr, RawExpression):
        return f'F.expr("{escape_string(expr.value)}")'
    if isinstance(expr, UnaryOp):
        operand = emit_expression(expr.operand, function_map)
        if expr.op == "not":
            return f"(~{operand})"
        return f"({expr.op}{operand})"
    if isinstance(expr, BinaryOp):
        left = emit_expression(expr.left, function_map)
        right = emit_expression(expr.right, function_map)
        op = map_operator(expr.op)
        return f"({left} {op} {right})"
    if isinstance(expr, FunctionCall):
        mapped = function_map.get(expr.name.lower(), expr.name)
        args = ", ".join(emit_expression(arg, function_map) for arg in expr.args)
        return f"F.{mapped}({args})"
    if isinstance(expr, CaseWhen):
        condition = emit_expression(expr.condition, function_map)
        then_expr = emit_expression(expr.then_expr, function_map)
        if expr.else_expr is None:
            else_expr = "F.lit(None)"
        else:
            else_expr = emit_expression(expr.else_expr, function_map)
        return f"F.when({condition}, {then_expr}).otherwise({else_expr})"
    raise ValueError(f"Unsupported expression: {expr}")


def map_operator(op: str) -> str:
    op_lower = op.lower()
    mapping = {
        "=": "==",
        "==": "==",
        "!=": "!=",
        "<>": "!=",
        "~=": "!=",
        "^=": "!=",
        "and": "&",
        "or": "|",
    }
    return mapping.get(op_lower, op)


def escape_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
