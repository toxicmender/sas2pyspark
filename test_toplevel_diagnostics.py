#!/usr/bin/env python
"""Test for unsupported top-level statement handling."""

from translator.diagnostics import DiagnosticCategory, get_global_diagnostics, reset_diagnostics
from translator.parser import ASTBuilder, SASParser
from translator.semantic.lower import SASLowerer


def test_unsupported_top_level_statements():
    """Test that unsupported top-level statements generate diagnostics."""

    # Reset diagnostics
    reset_diagnostics()

    sas_code = """
    options pagesize=60 linesize=80;
    libname mylib '/data/mydata';

    data output;
        set input;
        x = 1;
    run;

    proc sort data=output;
        by x;
    run;
    """

    # Parse the code
    parser = SASParser()
    ast_dict = parser.parse(sas_code)
    print("\n=== AST Structure ===")
    print(f"Root type: {ast_dict['type']}")
    print(f"Number of children: {len(ast_dict['children'])}")
    for i, child in enumerate(ast_dict["children"]):
        print(f"  {i}: {child['type']} - {child['text'][:50]}...")

    # Build typed AST
    ast_root = ASTBuilder.build_from_dict(ast_dict)

    # Lower to IR
    lowerer = SASLowerer()
    ir_program = lowerer.lower_program(ast_root)

    # Get diagnostics
    diagnostics = get_global_diagnostics()

    print("\n=== Diagnostics Report ===")
    print(diagnostics.format_detailed())

    # Verify we have diagnostics for unsupported statements
    unsupported_warnings = diagnostics.get_by_category(DiagnosticCategory.UNSUPPORTED_TOP_LEVEL)

    print(f"\n=== Unsupported Statement Diagnostics ===")
    print(f"Number of unsupported statement warnings: {len(unsupported_warnings)}")
    for diag in unsupported_warnings:
        print(f"  - {diag.message}")
        print(f"    Source: {diag.source_text[:60] if diag.source_text else 'N/A'}...")
        print(f"    Suggestion: {diag.suggestion}")

    # We should have at least 2 unsupported statement diagnostics:
    # 1. options statement
    # 2. libname statement
    # 3. proc sort
    assert len(unsupported_warnings) >= 2, (
        f"Expected at least 2 unsupported warnings, got {len(unsupported_warnings)}"
    )

    # Check that the diagnostics mention specific statement types
    messages = [d.message for d in unsupported_warnings]
    message_str = " ".join(messages)

    # Should mention OPTIONS and LIBNAME
    assert "options" in message_str.lower() or "libname" in message_str.lower(), (
        f"Expected OPTIONS or LIBNAME in diagnostics, got: {message_str}"
    )

    print("\n[PASS] Test passed: Unsupported top-level statements generate diagnostics")


if __name__ == "__main__":
    test_unsupported_top_level_statements()
