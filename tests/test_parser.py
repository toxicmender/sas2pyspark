from translator.ast import (
    AssignmentStatement,
    BinaryOp,
    ByStatement,
    DataStep,
    DeleteStatement,
    DropStatement,
    Identifier,
    IfStatement,
    KeepStatement,
    MergeStatement,
    NumberLiteral,
    OutputStatement,
    ProcStep,
    RawStatement,
    SetStatement,
    StringLiteral,
)
from translator.diagnostics import DiagnosticLevel
from translator.parser import parse_source


def test_parse_data_step_if_else():
    source = """
    data sales_final;
        set sales_2024;
        if revenue > 1000 then category='HIGH';
        else category='LOW';
    run;
    """
    result = parse_source(source)
    assert result.diagnostics == []
    assert len(result.ast.statements) == 1

    data_step = result.ast.statements[0]
    assert isinstance(data_step, DataStep)
    assert data_step.outputs == ["sales_final"]

    assert isinstance(data_step.statements[0], SetStatement)
    assert data_step.statements[0].datasets == ["sales_2024"]

    if_stmt = data_step.statements[1]
    assert isinstance(if_stmt, IfStatement)

    condition = if_stmt.condition
    assert isinstance(condition, BinaryOp)
    assert isinstance(condition.left, Identifier)
    assert condition.left.name == "revenue"
    assert condition.op == ">"
    assert isinstance(condition.right, NumberLiteral)
    assert condition.right.value == 1000

    consequence = if_stmt.consequence
    assert isinstance(consequence, AssignmentStatement)
    assert consequence.target == "category"
    assert isinstance(consequence.expression, StringLiteral)
    assert consequence.expression.value == "HIGH"

    alternative = if_stmt.alternative
    assert isinstance(alternative, AssignmentStatement)
    assert alternative.target == "category"
    assert isinstance(alternative.expression, StringLiteral)
    assert alternative.expression.value == "LOW"


def test_parse_proc_step():
    source = """
    proc sort data=work.sales;
        by id;
    run;
    """
    result = parse_source(source)

    assert result.diagnostics == []
    assert len(result.ast.statements) == 1
    proc_step = result.ast.statements[0]
    assert isinstance(proc_step, ProcStep)
    assert proc_step.name == "sort"
    assert proc_step.options == "data=work.sales"
    assert len(proc_step.statements) == 1
    assert isinstance(proc_step.statements[0], RawStatement)
    assert proc_step.statements[0].text == "by id"


def test_parse_data_step_merge_by_keep_drop():
    source = """
    data out;
        merge a b;
        by id;
        keep id name;
        drop temp;
    run;
    """
    result = parse_source(source)

    assert result.diagnostics == []
    data_step = result.ast.statements[0]
    assert isinstance(data_step, DataStep)

    assert isinstance(data_step.statements[0], MergeStatement)
    assert data_step.statements[0].datasets == ["a", "b"]

    assert isinstance(data_step.statements[1], ByStatement)
    assert data_step.statements[1].columns == ["id"]

    assert isinstance(data_step.statements[2], KeepStatement)
    assert data_step.statements[2].columns == ["id", "name"]

    assert isinstance(data_step.statements[3], DropStatement)
    assert data_step.statements[3].columns == ["temp"]


def test_parse_output_delete_in_if():
    source = """
    data out;
        set input;
        if flag then output out1;
        else delete;
    run;
    """
    result = parse_source(source)

    assert result.diagnostics == []
    data_step = result.ast.statements[0]
    if_stmt = data_step.statements[1]

    assert isinstance(if_stmt, IfStatement)
    assert isinstance(if_stmt.consequence, OutputStatement)
    assert if_stmt.consequence.target == "out1"
    assert isinstance(if_stmt.alternative, DeleteStatement)


def test_parse_dataset_options_stripped():
    source = """
    data out;
        set work.sales(where=(a>1)) other;
    run;
    """
    result = parse_source(source)

    assert result.diagnostics == []
    data_step = result.ast.statements[0]
    set_stmt = data_step.statements[0]
    assert isinstance(set_stmt, SetStatement)
    assert set_stmt.datasets == ["work.sales", "other"]


def test_else_without_if_emits_error():
    source = """
    data out;
        else status='N';
    run;
    """
    result = parse_source(source)

    assert any(
        diagnostic.level == DiagnosticLevel.ERROR and "ELSE" in diagnostic.message
        for diagnostic in result.diagnostics
    )
