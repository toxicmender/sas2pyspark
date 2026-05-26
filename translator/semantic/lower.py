from __future__ import annotations

from dataclasses import dataclass

from ..ast import (
    AssignmentStatement,
    ByStatement,
    CaseWhen,
    DataStep,
    DeleteStatement,
    DropStatement,
    Expression,
    Identifier,
    IfStatement,
    KeepStatement,
    MergeStatement,
    OutputStatement,
    ProcStep,
    RawExpression,
    RawStatement,
    SetStatement,
    SourceFile,
    Statement,
    UnaryOp,
)
from ..diagnostics import Diagnostic, DiagnosticLevel
from ..ir.nodes import (
    AssignmentNode,
    ConditionalWriteNode,
    DatasetNode,
    DropNode,
    FilterNode,
    IRNode,
    IRPlan,
    JoinNode,
    KeepNode,
    UnionNode,
    WriteNode,
)


@dataclass
class LowerResult:
    plans: list[IRPlan]
    diagnostics: list[Diagnostic]


def lower_source(source: SourceFile) -> LowerResult:
    diagnostics: list[Diagnostic] = []
    plans: list[IRPlan] = []

    for statement in source.statements:
        if isinstance(statement, DataStep):
            plan = lower_data_step(statement)
            plans.append(plan)
            diagnostics.extend(plan.diagnostics)
            continue
        if isinstance(statement, ProcStep):
            diagnostics.append(
                Diagnostic(
                    DiagnosticLevel.WARNING,
                    f"PROC step '{statement.name}' is not lowered in this phase",
                )
            )
            continue
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.WARNING,
                f"Unsupported top-level statement in lowering: {statement}",
            )
        )

    if not plans:
        diagnostics.append(
            Diagnostic(DiagnosticLevel.ERROR, "No DATA step found in source")
        )

    return LowerResult(plans=plans, diagnostics=diagnostics)


def lower_data_step(data_step: DataStep) -> IRPlan:
    diagnostics: list[Diagnostic] = []
    transforms: list[IRNode] = []

    set_statements = [
        stmt for stmt in data_step.statements if isinstance(stmt, SetStatement)
    ]
    merge_statements = [
        stmt for stmt in data_step.statements if isinstance(stmt, MergeStatement)
    ]
    by_statements = [
        stmt for stmt in data_step.statements if isinstance(stmt, ByStatement)
    ]

    if len(set_statements) > 1:
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.WARNING,
                "Multiple SET statements found; only the first is translated",
            )
        )
    if len(merge_statements) > 1:
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.WARNING,
                "Multiple MERGE statements found; only the first is translated",
            )
        )
    if len(by_statements) > 1:
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.WARNING,
                "Multiple BY statements found; only the first is used",
            )
        )

    by_keys = by_statements[0].columns if by_statements else []

    source = DatasetNode("")
    if merge_statements:
        if set_statements:
            diagnostics.append(
                Diagnostic(
                    DiagnosticLevel.WARNING,
                    "Both MERGE and SET statements found; MERGE takes precedence",
                )
            )
        datasets = merge_statements[0].datasets
        if not datasets:
            diagnostics.append(
                Diagnostic(DiagnosticLevel.ERROR, "MERGE statement missing datasets")
            )
        else:
            source = DatasetNode(datasets[0])
            if len(datasets) > 1:
                if not by_keys:
                    diagnostics.append(
                        Diagnostic(
                            DiagnosticLevel.WARNING,
                            "MERGE without BY keys; join keys are empty",
                        )
                    )
                for dataset in datasets[1:]:
                    transforms.append(JoinNode(dataset, by_keys, "outer"))
    elif set_statements:
        datasets = set_statements[0].datasets
        if not datasets:
            diagnostics.append(
                Diagnostic(DiagnosticLevel.ERROR, "SET statement missing datasets")
            )
        else:
            source = DatasetNode(datasets[0])
            for dataset in datasets[1:]:
                transforms.append(UnionNode(dataset))
    else:
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.ERROR, "DATA step missing SET or MERGE statement"
            )
        )

    if by_statements and not merge_statements:
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.WARNING,
                "BY statement is only used for MERGE in this phase",
            )
        )

    target = data_step.outputs[0] if data_step.outputs else ""
    if not target:
        diagnostics.append(
            Diagnostic(DiagnosticLevel.ERROR, "DATA step missing output dataset name")
        )

    if len(data_step.outputs) > 1:
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.WARNING,
                "Multiple DATA outputs found; additional outputs are written explicitly",
            )
        )
        for extra_output in data_step.outputs[1:]:
            transforms.append(WriteNode(extra_output))

    for stmt in data_step.statements:
        if isinstance(stmt, (SetStatement, MergeStatement, ByStatement)):
            continue
        if isinstance(stmt, AssignmentStatement):
            transforms.append(AssignmentNode(stmt.target, stmt.expression))
            continue
        if isinstance(stmt, IfStatement):
            transforms.extend(lower_if_statement(stmt, diagnostics))
            continue
        if isinstance(stmt, KeepStatement):
            transforms.append(KeepNode(stmt.columns))
            continue
        if isinstance(stmt, DropStatement):
            transforms.append(DropNode(stmt.columns))
            continue
        if isinstance(stmt, OutputStatement):
            transforms.extend(lower_output_statement(stmt, target, diagnostics))
            continue
        if isinstance(stmt, DeleteStatement):
            transforms.append(FilterNode(RawExpression("false")))
            continue
        if isinstance(stmt, RawStatement):
            diagnostics.append(
                Diagnostic(
                    DiagnosticLevel.WARNING,
                    f"Unsupported DATA step statement in lowering: {stmt.text}",
                )
            )
            continue
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.WARNING,
                f"Unsupported DATA step statement in lowering: {stmt}",
            )
        )

    return IRPlan(
        source=source, transforms=transforms, target=target, diagnostics=diagnostics
    )


def lower_output_statement(
    stmt: OutputStatement, default_target: str, diagnostics: list[Diagnostic]
) -> list[IRNode]:
    if stmt.target is None:
        return []
    if stmt.target == default_target:
        diagnostics.append(
            Diagnostic(
                DiagnosticLevel.WARNING,
                "Explicit OUTPUT to the default target is approximated",
            )
        )
        return []
    return [WriteNode(stmt.target)]


def lower_if_statement(
    stmt: IfStatement, diagnostics: list[Diagnostic]
) -> list[IRNode]:
    condition = stmt.condition
    consequence = stmt.consequence
    alternative = stmt.alternative

    if isinstance(consequence, AssignmentStatement):
        if alternative is None:
            expr = CaseWhen(
                condition, consequence.expression, Identifier(consequence.target)
            )
            return [AssignmentNode(consequence.target, expr)]
        if (
            isinstance(alternative, AssignmentStatement)
            and alternative.target == consequence.target
        ):
            expr = CaseWhen(condition, consequence.expression, alternative.expression)
            return [AssignmentNode(consequence.target, expr)]

    nodes: list[IRNode] = []
    nodes.extend(lower_branch_statement(consequence, condition, True, diagnostics))
    if alternative is not None:
        nodes.extend(lower_branch_statement(alternative, condition, False, diagnostics))
    return nodes


def lower_branch_statement(
    statement: Statement,
    condition: Expression,
    when_true: bool,
    diagnostics: list[Diagnostic],
) -> list[IRNode]:
    nodes: list[IRNode] = []
    predicate = condition if when_true else invert_condition(condition)

    if isinstance(statement, AssignmentStatement):
        column = statement.target
        if when_true:
            expr = CaseWhen(condition, statement.expression, Identifier(column))
        else:
            expr = CaseWhen(condition, Identifier(column), statement.expression)
        nodes.append(AssignmentNode(column, expr))
        return nodes

    if isinstance(statement, OutputStatement):
        if statement.target is None:
            return []
        nodes.append(ConditionalWriteNode(statement.target, predicate))
        return nodes

    if isinstance(statement, DeleteStatement):
        nodes.append(FilterNode(invert_condition(predicate)))
        return nodes

    diagnostics.append(
        Diagnostic(
            DiagnosticLevel.WARNING,
            "IF branch statement is unsupported in this phase",
        )
    )
    return nodes


def invert_condition(condition: Expression) -> Expression:
    return UnaryOp("not", condition)
