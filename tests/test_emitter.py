from translator.ast import BinaryOp, Identifier
from translator.emitters.pyspark import PySparkEmitter, emit_expression


def test_emit_expression_arithmetic():
    expr = BinaryOp(Identifier("a"), "+", Identifier("b"))
    output = emit_expression(expr, PySparkEmitter.with_default_map().function_map)
    assert output == '(F.col("a") + F.col("b"))'
