#!/usr/bin/env python3
"""
Build script for Tree-sitter SAS grammar using Rust and Cargo.

This script compiles the grammar.js into a binary parser library
that can be used by the Python translator via ctypes.

Requirements:
    - Rust 1.70+ (https://rustup.rs/)
    - tree-sitter-cli (cargo install tree-sitter-cli)

Usage:
    python scripts/build-grammar.py
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


def check_rust_installed():
    """Check if Rust/Cargo is installed."""
    try:
        result = subprocess.run(["rustc", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_tree_sitter_cli():
    """Check if tree-sitter CLI is installed."""
    try:
        result = subprocess.run(
            ["tree-sitter", "--version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_dependencies():
    """Install Rust dependencies."""
    print("Installing Rust dependencies...")
    result = subprocess.run(["cargo", "fetch"], capture_output=True, text=True, timeout=120)
    return result.returncode == 0


def generate_grammar(grammar_dir):
    """Generate parser.c from grammar.js using tree-sitter CLI."""
    print("Generating parser from grammar.js...")

    try:
        result = subprocess.run(
            ["tree-sitter", "generate", str(grammar_dir)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print(f"Error: tree-sitter generate failed:\n{result.stderr}", file=sys.stderr)
            return False

        print("✓ Grammar generated successfully (parser.c created)")
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


def build_rust_library(grammar_dir):
    """Build the Rust library using Cargo."""
    print("Building Rust library with Cargo (release mode)...")

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

        print("✓ Rust library built successfully")
        return True

    except subprocess.TimeoutExpired:
        print("Error: cargo build timed out (>5 minutes)", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Error: Cargo not found. Install Rust from https://rustup.rs/", file=sys.stderr)
        return False


def find_compiled_library(grammar_dir):
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


def main():
    # Get the project root
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    grammar_dir = project_root / "tree-sitter-sas"

    if not grammar_dir.exists():
        print(f"Error: Grammar directory not found at {grammar_dir}", file=sys.stderr)
        return False

    if not (grammar_dir / "grammar.js").exists():
        print(f"Error: grammar.js not found at {grammar_dir}", file=sys.stderr)
        return False

    print("=" * 70)
    print("Building Tree-sitter SAS Grammar")
    print("=" * 70)

    # Check prerequisites
    print("\nChecking prerequisites...")

    if not check_rust_installed():
        print(
            "Error: Rust not installed.",
            "Install from https://rustup.rs/ or via: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
            file=sys.stderr,
        )
        return False
    print("✓ Rust installed")

    if not check_tree_sitter_cli():
        print(
            "Error: tree-sitter CLI not installed.",
            "Install with: cargo install tree-sitter-cli",
            file=sys.stderr,
        )
        return False
    print("✓ tree-sitter CLI installed")

    # Build steps
    print(f"\nGrammar directory: {grammar_dir}")

    # Generate parser from grammar.js
    if not generate_grammar(grammar_dir):
        return False

    # Install Rust dependencies
    print("\nInstalling Rust dependencies...")
    if not install_dependencies():
        print("Warning: cargo fetch failed (may continue anyway)", file=sys.stderr)

    # Build Rust library
    print()
    if not build_rust_library(grammar_dir):
        return False

    # Verify compiled library
    print("\nVerifying compiled library...")
    lib_path = find_compiled_library(grammar_dir)

    if not lib_path or not lib_path.exists():
        print(f"Error: Compiled library not found", file=sys.stderr)
        return False

    print(f"✓ Compiled library found: {lib_path}")

    # Run Rust tests
    print("\nRunning Rust tests...")
    result = subprocess.run(
        ["cargo", "test", "--release"], cwd=grammar_dir, capture_output=True, text=True, timeout=120
    )

    if result.returncode == 0:
        print("✓ All Rust tests passed")
    else:
        print("Warning: Some Rust tests failed", file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    print()
    print("=" * 70)
    print("Build Complete!")
    print("=" * 70)
    print(f"\nCompiled library: {lib_path}")
    print(f"\nThe Python parser will automatically find and use this library.")
    print(f"\nNext steps:")
    print(f"  1. Run Python tests: uv run pytest tree-sitter-sas/test/ -v")
    print(f"  2. Or use the parser: from translator.parser import SASParser")
    print()

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
