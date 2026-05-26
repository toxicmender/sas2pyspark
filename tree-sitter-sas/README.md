# Tree-sitter SAS Grammar

This directory contains the Tree-sitter grammar definition for the SAS language, built with Rust and Cargo.

## Structure

- `grammar.js` - Complete SAS grammar definition with operator precedence
- `Cargo.toml` - Rust project configuration
- `build.rs` - Build script for compiling grammar with C
- `src/lib.rs` - Rust library binding
- `src/parser.c` - Generated parser (created by tree-sitter CLI)
- `examples/parse.rs` - Example Rust parser usage
- `queries/` - Query files for syntax highlighting and scope tracking
  - `highlights.scm` - Syntax highlighting
  - `locals.scm` - Scope tracking
- `test/` - Test files for grammar validation
  - `test_expressions.py` - Python unit tests for expression parsing
  - `corpus.txt` - Golden tests for parser

## Building the Grammar

### Prerequisites

- **Rust 1.70+**: Install from [https://rustup.rs/](https://rustup.rs/)
  ```bash
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  ```

- **tree-sitter CLI**: Install with Cargo
  ```bash
  cargo install tree-sitter-cli
  ```

### Build Steps

From the project root:

```bash
# Method 1: Use the Python build script (recommended)
python scripts/build-grammar.py

# Method 2: Manual Cargo build
cd tree-sitter-sas
cargo build --release
cd ..
```

The build script will:
1. Check for Rust and tree-sitter CLI
2. Generate `parser.c` from `grammar.js`
3. Compile the Rust library
4. Run tests
5. Output the compiled library path

### Output

Successful build produces:
- **Linux/Unix**: `tree-sitter-sas/target/release/libtree_sitter_sas.so`
- **macOS**: `tree-sitter-sas/target/release/libtree_sitter_sas.dylib`
- **Windows**: `tree-sitter-sas/target/release/tree_sitter_sas.dll`

These libraries are automatically discovered and loaded by the Python parser.

## Using the Build Script

The Python build script handles the complete workflow:

```bash
uv run python scripts/build-grammar.py
```

This:
- Verifies Rust/Cargo and tree-sitter CLI are installed
- Generates parser from grammar.js
- Builds optimized release binary
- Runs test suite
- Reports library location
- Guides next steps

## Running Tests

### Rust tests
```bash
# Run library tests
cd tree-sitter-sas
cargo test --release
cd ..
```

### Python tests
```bash
# Test expression parsing (requires compiled grammar)
uv run pytest tree-sitter-sas/test/test_expressions.py -v
```

## Implementation Phases

### Phase B: Expression Grammar ✅ COMPLETE
- [x] Operator precedence table (10 levels)
- [x] Literal rules (string, number)
- [x] Function call grammar
- [x] Expression parsing rules
- [x] Tests for operators and precedence

### Phase A: Grammar Skeleton (PLANNED)
- [ ] Full statement rules (data_step, proc_step, etc.)
- [ ] Integration with parser wrapper
- [ ] Tests for statement parsing

### Phase C: Macro Grammar (PLANNED)
- [ ] Macro definition and invocation rules
- [ ] Macro variable substitution
- [ ] Tree-sitter injection or external grammar
- [ ] Macro expansion integration

## Grammar Features

### Literals
- Numbers: `123`, `123.456`, `1.23e10`, `1e-5`
- Strings: `"text"`, `'text'`, `'it''s'` (single quote escape)
- Comments: `* comment;`, `/* multi-line */`

### Operators (by precedence, lowest to highest)
1. **Logical OR**: `or`
2. **Logical AND**: `and`
3. **Logical NOT**: `not`
4. **Comparison**: `=`, `^=`, `~=`, `<`, `>`, `<=`, `>=`, `==`, `in`, `contains`
5. **Concatenation**: `||`
6. **Addition/Subtraction**: `+`, `-`
7. **Multiplication/Division**: `*`, `/`
8. **Exponentiation**: `**` (right-associative)
9. **Unary**: `-`, `+`, `not`

### Statements
- DATA STEP with SET/MERGE, assignments, IF/THEN/ELSE, DO loops
- PROC STEP with VAR, CLASS, WHERE statements
- Output, Keep, Drop, Format, Length statements

## Development Workflow

### Modifying the Grammar

1. Edit `grammar.js`
2. Regenerate parser:
   ```bash
   tree-sitter generate tree-sitter-sas
   ```
3. Rebuild Rust library:
   ```bash
   cd tree-sitter-sas && cargo build --release && cd ..
   ```
4. Run tests:
   ```bash
   uv run pytest tree-sitter-sas/test/ -v
   ```

### Adding Tests

Add test cases to `test/test_expressions.py` and run:
```bash
uv run pytest tree-sitter-sas/test/test_expressions.py -v
```

## Troubleshooting

### "Rust not installed"
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### "tree-sitter CLI not found"
```bash
cargo install tree-sitter-cli
```

### Build fails with C compilation errors
```bash
# Ensure build tools are installed
# Windows: Visual Studio Build Tools
# macOS: Xcode Command Line Tools (xcode-select --install)
# Linux: build-essential (sudo apt install build-essential)
```

### Parser library not found at runtime
1. Ensure build completed successfully
2. Check library exists: `ls tree-sitter-sas/target/release/`
3. Re-run Python build script to verify paths

## Next Steps

1. Build grammar: `python scripts/build-grammar.py`
2. Run tests: `uv run pytest tree-sitter-sas/test/ -v`
3. Use parser: `from translator.parser import SASParser`
4. Implement Phase A statement parsing
5. Add Phase C macro support
