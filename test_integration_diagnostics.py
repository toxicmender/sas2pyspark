#!/usr/bin/env python
"""Integration test: Verify diagnostics work with full translation pipeline."""

from pathlib import Path

from translator.diagnostics import get_global_diagnostics, reset_diagnostics
from translator.emitters import PySparkEmitter
from translator.parser import ASTBuilder, SASParser
from translator.semantic.lower import SASLowerer


def test_full_translation_pipeline():
    """Test that diagnostics work through the full translation pipeline."""

    reset_diagnostics()

    sas_code = """
    options pagesize=80;
    libname work '/tmp/work';

    data output;
        set input;
        x = y + 1;
    run;

    proc sort data=output;
        by x;
    run;
    """

    # Parse
    parser = SASParser()
    ast_dict = parser.parse(sas_code)
    ast_root = ASTBuilder.build_from_dict(ast_dict)

    # Lower
    lowerer = SASLowerer()
    ir_program = lowerer.lower_program(ast_root)

    # Emit
    emitter = PySparkEmitter()
    pyspark_code = emitter.emit_program(ir_program)

    # Get diagnostics
    diagnostics = get_global_diagnostics()

    print("\n=== Full Translation Pipeline ===")
    print(f"AST children: {len(ast_root.children)}")
    print(f"IR steps: {len(ir_program.get_steps())}")
    print(f"Generated lines of code: {len(pyspark_code.split(chr(10)))}")
    print(f"\n=== Diagnostics ===")
    print(diagnostics.format_summary())

    # Verify we got diagnostics
    unsupported = diagnostics.get_by_category(
        __import__(
            "translator.diagnostics", fromlist=["DiagnosticCategory"]
        ).DiagnosticCategory.UNSUPPORTED_TOP_LEVEL
    )

    assert len(unsupported) >= 2, (
        f"Expected at least 2 unsupported warnings, got {len(unsupported)}"
    )

    print("\n[PASS] Full translation pipeline works with diagnostics")


if __name__ == "__main__":
    test_full_translation_pipeline()
