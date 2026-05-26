# sas2pyspark

Initial-phase SAS to PySpark translation framework based on the project specification.

## Usage

```sh
python main.py path/to/input.sas -o output.py
```

Diagnostics are printed to stderr.

## Development

```sh
uv sync --extra dev
uv run pytest
```

## Current coverage (initial phase)

- DATA step parsing (single DATA step)
- `SET` statements (first dataset only)
- Assignments and `IF/ELSE` assignments
- Expression parsing for basic arithmetic and comparisons
- PySpark emission using DataFrame APIs
