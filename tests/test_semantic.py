from translator.ast import CaseWhen
from translator.ir.nodes import AssignmentNode
from translator.parser import parse_source
from translator.semantic.lower import lower_source


def test_lower_if_else_assignment_to_case_when():
    source = """
    data sales_final;
        set sales_2024;
        if revenue > 1000 then category='HIGH';
        else category='LOW';
    run;
    """
    parse_result = parse_source(source)
    lower_result = lower_source(parse_result.ast)

    assert len(lower_result.plans) == 1
    plan = lower_result.plans[0]

    assert plan.source.name == "sales_2024"
    assert plan.target == "sales_final"
    assert len(plan.transforms) == 1

    assignment = plan.transforms[0]
    assert isinstance(assignment, AssignmentNode)
    assert assignment.column == "category"
    assert isinstance(assignment.expression, CaseWhen)
