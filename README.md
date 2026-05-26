# SAS to PySpark Translator

A compiler-style framework for translating SAS programs into PySpark code using tree-sitter for syntactic parsing and semantic analysis.

## Overview

This project implements the initial phase of a SAS to PySpark translation system targeting Apache Spark and Databricks runtime environments. It uses a multi-stage architecture:

1. **Lexical & Syntax Analysis** - Tree-sitter for parsing
2. **Semantic Analysis** - Variable scope, dataset lineage, and execution semantics
3. **Intermediate Representation** - IR nodes for logical transformation
4. **Code Generation** - PySpark DataFrame API emission

## Requirements

- Python 3.12+
- PySpark 3.5+
- Databricks SDK 0.30+
- tree-sitter 0.21+

## Installation

Using `uv` (recommended):

```bash
# Install base dependencies
uv sync

# Install with development dependencies (testing, formatting, type checking)
uv sync --extra dev
```

## Quick Start

### Translating SAS Code

```python
from pathlib import Path
from main import SASTranslator

# Create translator instance
translator = SASTranslator()

# Translate a single file
pyspark_code = translator.translate_file(Path("input.sas"))

# Or translate a directory
translator.translate_directory(
    Path("sas_scripts/"),
    Path("pyspark_scripts/")
)
```

### Using IR Directly

```python
from translator.ir import DatasetNode, FilterNode, ProjectionNode, IRProgram
from translator.emitters import PySparkEmitter

# Create IR pipeline
dataset = DatasetNode("input_table")
filtered = FilterNode("F.col('active') == True", dataset)
projected = ProjectionNode(["id", "name"], filtered, keep=True)

# Generate PySpark code
emitter = PySparkEmitter()
pyspark_code = emitter.emit_node(projected)
print(emitter.get_generated_code())
```

## Architecture

### Core Modules

#### `translator/ir/`
Intermediate Representation layer with node types:
- `DatasetNode` - Source/sink tables
- `FilterNode` - WHERE/IF predicates
- `ProjectionNode` - Column selection (KEEP/DROP)
- `AssignmentNode` - Variable/column assignments
- `JoinNode` - MERGE operations
- `SortNode` - Sort/ORDER operations
- `AggregateNode` - PROC aggregations
- `RenameNode` - Column renaming
- `UnionNode` - Dataset concatenation

#### `translator/semantic/`
Semantic analysis layer:
- `SemanticContext` - Tracks datasets, variables, scopes
- `SemanticAnalyzer` - Analyzes SAS statements
- `Variable` - SAS variable metadata
- `DatasetMetadata` - Dataset structure information
- Support for automatic variables (_N_, _ERROR_, etc.)
- Variable scope resolution (GLOBAL, DATA_STEP, PROC_STEP, MACRO)

#### `translator/emitters/`
Code generation:
- `PySparkEmitter` - Generates PySpark DataFrame code
- Supports all IR node types
- Generates valid Python code with proper imports

#### `translator/parser.py`
Parsing layer:
- `SASParser` - Tree-sitter wrapper for SAS code
- `ASTBuilder` - Builds typed AST from parsed output
- `ASTNode` - Typed AST node representation

### Main Entry Point

`main.py` contains:
- `SASTranslator` - Orchestrates the full translation pipeline
- Methods for single file and directory translation

## Testing

### Running Tests

```bash
# Run all tests with coverage
uv run pytest tests/ -v --cov=translator

# Run specific test file
uv run pytest tests/test_ir.py -v

# Run with short traceback
uv run pytest tests/ --tb=short
```

### Test Coverage

Current coverage: **93%**

Test suites:
- **test_ir.py** - IR node construction and operations (37 tests)
- **test_semantic.py** - Semantic analysis and context (27 tests)
- **test_emitters.py** - PySpark code generation (19 tests)
- **test_translator.py** - End-to-end translation (6 tests)

Total: **71 passing tests**

### Example Test

```python
def test_translate_simple_source():
    translator = SASTranslator()
    
    sas_code = """
    data output;
        set input;
    run;
    """
    
    pyspark_code = translator.translate_source(sas_code)
    
    assert "spark.table" in pyspark_code
    assert "saveAsTable" in pyspark_code
```

## Supported Constructs (MVP)

### DATA Step
- ✅ Basic dataset operations (SET, MERGE)
- ✅ Variable assignments
- ✅ IF/THEN/ELSE conditions
- ✅ BY-group processing
- ✅ KEEP/DROP statements
- ⚠️ Partial RETAIN support
- ⚠️ FIRST./LAST. semantics deferred

### PROC Steps
- ✅ PROC SORT (→ orderBy)
- ✅ PROC FREQ (→ groupBy/count)
- ✅ PROC MEANS (→ agg)
- ⚠️ PROC SQL deferred
- ⚠️ Custom PROCs deferred

### Translations
- ✅ Simple column selections
- ✅ Joins with multiple keys
- ✅ Aggregations
- ✅ Sorting/ordering
- ✅ Column renaming
- ⚠️ Complex macros deferred

## Unsupported Features

- ODS rendering
- CALL EXECUTE / DOSUBL
- Advanced macro recursion
- PROC FORMAT execution
- Hash objects
- SAS/GRAPH

## Project Structure

```
sas2pyspark/
├── translator/
│   ├── __init__.py           # Package exports
│   ├── parser.py             # Tree-sitter parsing
│   ├── ir/                   # IR node definitions
│   ├── semantic/             # Semantic analysis
│   └── emitters/             # Code generation
├── tests/
│   ├── test_ir.py            # IR tests
│   ├── test_semantic.py      # Semantic analysis tests
│   ├── test_emitters.py      # Code generation tests
│   └── test_translator.py    # End-to-end tests
├── main.py                   # Main translator interface
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Configuration

### `pyproject.toml`

- **Python**: 3.12+
- **Build System**: hatchling
- **Package Manager**: uv
- **Test Framework**: pytest with coverage
- **Code Style**: black, ruff
- **Type Checking**: mypy

### Development Setup

```bash
# Format code
uv run black translator/ tests/

# Lint code
uv run ruff check translator/ tests/

# Type check
uv run mypy translator/

# Run tests with coverage
uv run pytest tests/ --cov=translator --cov-report=term-missing
```

## Example Translation

### Input (SAS)

```sas
data sales_summary;
    set raw_sales;
    if amount > 1000 then category='HIGH';
    else category='LOW';
run;

proc sort data=sales_summary;
    by customer_id;
run;
```

### Output (PySpark)

```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import *

df_1 = spark.table("raw_sales")
df_1.write.mode("overwrite").saveAsTable("sales_summary")

df_2 = spark.table("sales_summary")
df_2 = df_2.orderBy(F.col("customer_id").asc())
df_2.write.mode("overwrite").saveAsTable("sales_summary")
```

## Future Enhancements

### Phase 2
- Full macro engine with expansion
- ARRAY support
- Advanced RETAIN optimization
- Date/time semantics

### Phase 3
- Full PROC SQL compatibility
- Cost-based optimization
- Lineage visualization
- Interactive migration diagnostics

## Development Notes

### Adding New IR Node Types

1. Create class in `translator/ir/__init__.py` inheriting from `IRNode`
2. Add corresponding emitter method in `translator/emitters/__init__.py`
3. Add tests in `tests/test_emitters.py`

### Adding New Tests

Tests should use pytest and follow naming convention:
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

## License

MIT

## References

- [Technical Specification](specification.md)
- [Apache Spark Python API](https://spark.apache.org/docs/latest/api/python/)
- [Tree-sitter](https://tree-sitter.github.io/)
- [Databricks Runtime](https://docs.databricks.com/)

## Troubleshooting

### Import Errors

If you encounter import errors, ensure dependencies are installed:

```bash
uv sync --extra dev
```

### Test Failures

Run with verbose output to debug:

```bash
uv run pytest tests/ -vv --tb=long
```

### PySpark Not Available

Ensure PySpark is installed in the environment:

```bash
uv pip install pyspark>=3.5.0
```

## Contributing

For contributing code, please:
1. Ensure all tests pass: `uv run pytest tests/`
2. Format code: `uv run black translator/ tests/`
3. Check types: `uv run mypy translator/`
