#!/usr/bin/env python3
"""Quick test to verify the parser works."""

from translator.parser import SASParser

# Test basic parsing
sas_code = """
data output;
    set input;
    keep var1 var2;
run;
"""

parser = SASParser()
ast = parser.parse(sas_code)

print("Parsing successful!")
print(f"AST type: {ast['type']}")
print(f"Number of top-level children: {len(ast['children'])}")

if ast["children"]:
    data_step = ast["children"][0]
    print(f"First child type: {data_step['type']}")
    print(f"DATA step has {len(data_step['children'])} statement children:")
    for stmt in data_step["children"]:
        print(f"  - {stmt['type']}: {stmt['text'][:50]}")
