from __future__ import annotations

from dataclasses import dataclass


class Statement:
    pass


class Expression:
    pass


@dataclass(frozen=True)
class RawExpression(Expression):
    value: str


@dataclass(frozen=True)
class SourceFile:
    statements: list[Statement]


@dataclass(frozen=True)
class RawStatement(Statement):
    text: str


@dataclass(frozen=True)
class ProcStep(Statement):
    name: str
    options: str | None
    statements: list[Statement]


@dataclass(frozen=True)
class DataStep(Statement):
    outputs: list[str]
    statements: list[Statement]


@dataclass(frozen=True)
class SetStatement(Statement):
    datasets: list[str]


@dataclass(frozen=True)
class MergeStatement(Statement):
    datasets: list[str]


@dataclass(frozen=True)
class ByStatement(Statement):
    columns: list[str]


@dataclass(frozen=True)
class KeepStatement(Statement):
    columns: list[str]


@dataclass(frozen=True)
class DropStatement(Statement):
    columns: list[str]


@dataclass(frozen=True)
class OutputStatement(Statement):
    target: str | None


@dataclass(frozen=True)
class DeleteStatement(Statement):
    pass


@dataclass(frozen=True)
class ElseStatement(Statement):
    statement: Statement | None


@dataclass(frozen=True)
class AssignmentStatement(Statement):
    target: str
    expression: Expression


@dataclass(frozen=True)
class IfStatement(Statement):
    condition: Expression
    consequence: Statement
    alternative: Statement | None


@dataclass(frozen=True)
class Identifier(Expression):
    name: str


@dataclass(frozen=True)
class NumberLiteral(Expression):
    value: float | int


@dataclass(frozen=True)
class StringLiteral(Expression):
    value: str


@dataclass(frozen=True)
class UnaryOp(Expression):
    op: str
    operand: Expression


@dataclass(frozen=True)
class BinaryOp(Expression):
    left: Expression
    op: str
    right: Expression


@dataclass(frozen=True)
class FunctionCall(Expression):
    name: str
    args: list[Expression]


@dataclass(frozen=True)
class CaseWhen(Expression):
    condition: Expression
    then_expr: Expression
    else_expr: Expression | None
