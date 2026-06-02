#!/usr/bin/env python3
"""
Build script for Tree-sitter SAS grammar using Rust and Cargo.

This script compiles the grammar.cjs into a binary parser library
that can be used by the Python translator via ctypes.

Requirements:
    - Rust 1.70+ (https://rustup.rs/)
    - tree-sitter-cli (cargo install tree-sitter-cli)
    - Node.js 18+ (required by tree-sitter-cli to parse grammar.cjs)
      Install from: https://nodejs.org/ or via package manager

Usage:
    python scripts/build-grammar.py

Troubleshooting:
    If tree-sitter-cli generate fails with "program not found" (Node.js):
    1. Install Node.js from https://nodejs.org/ (18+ LTS recommended)
    2. Verify: node --version && npm --version
    3. Re-run this script

    Alternatively, on Windows:
    - Use Chocolatey: choco install nodejs
    - Use Windows Package Manager: winget install OpenJS.NodeJS
    - Use WSL with your Linux package manager
"""

import platform
import subprocess
import sys
from pathlib import Path


def _print_safe(msg: str) -> None:
    """Print with UTF-8 encoding to handle special characters on Windows."""
    try:
        print(msg)
    except UnicodeEncodeError:
        # Fall back to ASCII-safe version on encoding errors
        msg_safe = msg.encode("utf-8", errors="replace").decode("ascii", errors="replace")
        print(msg_safe)


def check_rust_installed() -> bool:
    """Check if Rust/Cargo is installed."""
    try:
        result = subprocess.run(["rustc", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_tree_sitter_cli() -> bool:
    """Check if tree-sitter CLI is installed."""
    try:
        result = subprocess.run(
            ["tree-sitter", "--version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_node_installed() -> bool:
    """Check if Node.js is installed (required for tree-sitter generate)."""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_dependencies() -> bool:
    """Install Rust dependencies."""
    _print_safe("Installing Rust dependencies...")
    result = subprocess.run(["cargo", "fetch"], capture_output=True, text=True, timeout=120)
    return result.returncode == 0


def generate_grammar(grammar_dir: Path) -> bool:
    """Generate parser.c from grammar.cjs using tree-sitter CLI."""
    _print_safe("Generating parser from grammar.cjs...")

    try:
        # tree-sitter CLI requires the path to the grammar.cjs file
        grammar_file = grammar_dir / "grammar.cjs"
        result = subprocess.run(
            ["tree-sitter", "generate", str(grammar_file)],
            cwd=str(grammar_dir),
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            # Check if the error is due to missing Node.js
            if "program not found" in result.stderr and "node" in result.stderr:
                print(
                    "Error: Node.js is required but not found.",
                    "tree-sitter-cli uses Node.js to parse grammar.cjs",
                    "",
                    "Install Node.js from: https://nodejs.org/ (18+ LTS recommended)",
                    "",
                    "Or use a package manager:",
                    "  - macOS: brew install node",
                    "  - Windows (Chocolatey): choco install nodejs",
                    "  - Windows (winget): winget install OpenJS.NodeJS",
                    "  - Linux (apt): sudo apt install nodejs npm",
                    "",
                    file=sys.stderr,
                )
            else:
                print(f"Error: tree-sitter generate failed:\n{result.stderr}", file=sys.stderr)
            return False

        _print_safe("[OK] Grammar generated successfully (parser.c created)")
        return True

    except subprocess.TimeoutExpired:
        print("Error: tree-sitter generate timed out", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(
            "Error: tree-sitter CLI not found.",
            "Install with: cargo install tree-sitter-cli",
            file=sys.stderr,
        )
        return False


def build_rust_library(grammar_dir: Path) -> bool:
    """Build the Rust library using Cargo."""
    _print_safe("Building Rust library with Cargo (release mode)...")

    try:
        # Build in release mode for performance
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=grammar_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes
        )

        if result.returncode != 0:
            print(f"Error: cargo build failed:\n{result.stderr}", file=sys.stderr)
            return False

        _print_safe("[OK] Rust library built successfully")
        return True

    except subprocess.TimeoutExpired:
        print("Error: cargo build timed out (>5 minutes)", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Error: Cargo not found. Install Rust from https://rustup.rs/", file=sys.stderr)
        return False


def find_compiled_library(grammar_dir: Path):
    """Find the compiled library path."""
    # Determine platform-specific library name
    system = platform.system()
    if system == "Windows":
        lib_name = "tree_sitter_sas.dll"
        subdirs = ["target/release", "target/debug"]
    elif system == "Darwin":
        lib_name = "libtree_sitter_sas.dylib"
        subdirs = ["target/release", "target/debug"]
    else:  # Linux and others
        lib_name = "libtree_sitter_sas.so"
        subdirs = ["target/release", "target/debug"]

    for subdir in subdirs:
        lib_path = grammar_dir / subdir / lib_name
        if lib_path.exists():
            return lib_path

    return None


def main() -> bool:
    """Main build function."""
    # Get the project root
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    grammar_dir = project_root / "tree-sitter-sas"

    if not grammar_dir.exists():
        print(f"Error: Grammar directory not found at {grammar_dir}", file=sys.stderr)
        return False

    if not (grammar_dir / "grammar.cjs").exists():
        print(f"Error: grammar.cjs not found at {grammar_dir}", file=sys.stderr)
        return False

    _print_safe("=" * 70)
    _print_safe("Building Tree-sitter SAS Grammar")
    _print_safe("=" * 70)

    # Check prerequisites
    _print_safe("\nChecking prerequisites...")

    if not check_rust_installed():
        print(
            "Error: Rust not installed.",
            "Install from https://rustup.rs/ or via: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
            file=sys.stderr,
        )
        return False
    _print_safe("[OK] Rust installed")

    if not check_tree_sitter_cli():
        print(
            "Error: tree-sitter CLI not installed.",
            "Install with: cargo install tree-sitter-cli",
            file=sys.stderr,
        )
        return False
    _print_safe("[OK] tree-sitter CLI installed")

    if not check_node_installed():
        print(
            "Error: Node.js is required but not installed.",
            "tree-sitter-cli uses Node.js to parse grammar.cjs",
            "",
            "Install Node.js from: https://nodejs.org/ (18+ LTS recommended)",
            file=sys.stderr,
        )
        return False
    _print_safe("[OK] Node.js installed")

    # Build steps
    _print_safe(f"\nGrammar directory: {grammar_dir}")

    # Generate parser from grammar.cjs
    if not generate_grammar(grammar_dir):
        return False

    # Install Rust dependencies
    _print_safe("\nInstalling Rust dependencies...")
    if not install_dependencies():
        print("Warning: cargo fetch failed (may continue anyway)", file=sys.stderr)

    # Build Rust library
    _print_safe("")
    if not build_rust_library(grammar_dir):
        return False

    # Verify compiled library
    _print_safe("\nVerifying compiled library...")
    lib_path = find_compiled_library(grammar_dir)

    if not lib_path or not lib_path.exists():
        print("Error: Compiled library not found", file=sys.stderr)
        return False

    _print_safe(f"[OK] Compiled library found: {lib_path}")

    # Run Rust tests
    _print_safe("\nRunning Rust tests...")
    result = subprocess.run(
        ["cargo", "test", "--release"], cwd=grammar_dir, capture_output=True, text=True, timeout=120
    )

    if result.returncode == 0:
        _print_safe("[OK] All Rust tests passed")
    else:
        print("Warning: Some Rust tests failed", file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    _print_safe("")
    _print_safe("=" * 70)
    _print_safe("Build Complete!")
    _print_safe("=" * 70)
    _print_safe(f"\nCompiled library: {lib_path}")
    _print_safe("\nThe Python parser will automatically find and use this library.")
    _print_safe("\nNext steps:")
    _print_safe("  1. Run Python tests: uv run pytest tree-sitter-sas/test/ -v")
    _print_safe("  2. Or use the parser: from translator.parser import SASParser")
    _print_safe("")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nBuild cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)
