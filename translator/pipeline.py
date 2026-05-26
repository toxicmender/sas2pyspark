from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import Diagnostic
from .emitters.pyspark import PySparkEmitter
from .parser import parse_source
from .semantic.lower import lower_source


@dataclass
class TranslationResult:
    pyspark: str
    diagnostics: list[Diagnostic]


def translate_sas_to_pyspark(source: str) -> TranslationResult:
    parse_result = parse_source(source)
    lower_result = lower_source(parse_result.ast)
    diagnostics = parse_result.diagnostics + lower_result.diagnostics
    emitter = PySparkEmitter.with_default_map()
    pyspark_code = emitter.emit_program(lower_result.plans)
    return TranslationResult(pyspark=pyspark_code, diagnostics=diagnostics)
