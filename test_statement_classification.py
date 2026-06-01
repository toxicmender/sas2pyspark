#!/usr/bin/env python
"""Verify parser statement classification."""

from translator.parser import SASParser


def test_statement_classification():
    """Test that statements are properly classified by keyword."""

    sas_code = """
    options obs=100;
    libname mylib '/path/to/lib';
    filename input '/path/to/file.sas';
    
    data work.test;
        set source;
    run;
    
    proc means;
        var x;
    run;
    """

    parser = SASParser()
    ast_dict = parser.parse(sas_code)
    
    print("\n=== Statement Types ===")
    for i, child in enumerate(ast_dict["children"]):
        print(f"{i}: {child['type']:20} - {child['text'][:50]}...")
    
    # Verify statement types
    stmt_types = [child['type'] for child in ast_dict["children"]]
    
    expected_types = [
        'options_statement',
        'libname_statement', 
        'filename',  # Simple statements get classified by keyword alone
        'data_step',
        'proc_step',
    ]
    
    for expected in expected_types:
        assert expected in stmt_types, f"Expected {expected} in {stmt_types}"
    
    print("\n[PASS] All statement types properly classified")


if __name__ == "__main__":
    test_statement_classification()
