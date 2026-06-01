"""
Parser layer using tree-sitter for SAS syntax parsing.

Provides parsing and AST construction for SAS source code.

This module contains a graceful stub parser used when the compiled
Tree-sitter grammar is not available. The stub aims to produce a
useful top-level AST (DATA/PROC/LIBNAME/OPTIONS/other) so downstream
semantic passes have visibility into top-level statements instead of
silently seeing an empty source file.
"""

import platform
import re
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional


class SASParser:
    """Wrapper around tree-sitter SAS parser.

    Behavior:
    - Attempts to load the compiled Tree-sitter grammar (platform-specific
      shared library). If available, uses the real parser.
    - If the grammar or the Python `tree_sitter` package is missing, the
      parser falls back to a lightweight regex-based stub parser that
      recognises common top-level statements so the rest of the pipeline
      can make progress and emit clearer diagnostics.
    """

    def __init__(self):
        """Initialize the SAS parser.

        Attempts to load the compiled Tree-sitter SAS grammar.
        Falls back to stub parser if grammar is not available.
        """
        self.parser = None
        self.language = None
        self.grammar_loaded = False

        # Helpful build instructions used in warnings
        self._build_instructions = (
            "To build the Tree-sitter SAS grammar, run: python scripts/build-grammar.py\n"
            "This project uses a Rust/Cargo-based build. Ensure you have Rust + Cargo installed,\n"
            "and the tree-sitter CLI available (`cargo install tree-sitter-cli`). See: tree-sitter-sas/README.md"
        )

        try:
            # Import here so the package is optional at runtime
            from tree_sitter import Language, Parser  # type: ignore

            # Try to load the compiled SAS grammar
            grammar_path = self._find_compiled_grammar()
            if grammar_path and grammar_path.exists():
                try:
                    self.language = Language(str(grammar_path), "sas")
                    self.parser = Parser()
                    self.parser.set_language(self.language)
                    self.grammar_loaded = True
                except Exception as e:
                    warnings.warn(
                        f"Failed to load compiled Tree-sitter grammar: {e}. Using stub parser.\n"
                        f"{self._build_instructions}"
                    )
            else:
                warnings.warn(
                    "Tree-sitter SAS grammar not found. Using stub parser.\n"
                    f"{self._build_instructions}"
                )
        except ImportError:
            warnings.warn(
                "tree-sitter Python bindings not installed. Using stub parser.\n"
                "Install with: pip install tree-sitter\n"
                f"{self._build_instructions}"
            )

    @staticmethod
    def _find_compiled_grammar() -> Optional[Path]:
        """Find the compiled Tree-sitter grammar library.

        Tree-sitter builds platform-specific shared libraries. Different
        build setups may create files with different names. Try a few
        sensible candidates and common build output locations.
        """
        project_root = Path(__file__).parent.parent
        grammar_dir = project_root / "tree-sitter-sas"

        # Candidate basenames that appear across different build systems
        candidate_basenames = [
            "libtree_sitter_sas",
            "tree_sitter_sas",
            "tree-sitter-sas",
            "sas",
            "tree_sitter_sas_binding",
        ]

        exts = ["dll", "so", "dylib"]

        candidate_filenames = []
        for base in candidate_basenames:
            for ext in exts:
                candidate_filenames.append(f"{base}.{ext}")

        # Common build output directories to check
        search_dirs = [
            grammar_dir / "target" / "release",
            grammar_dir / "target" / "debug",
            grammar_dir / "build" / "Release",
            grammar_dir / "build",
            grammar_dir / "src",
            grammar_dir,
        ]

        for d in search_dirs:
            if not d.exists():
                continue
            for name in candidate_filenames:
                lib_path = d / name
                if lib_path.exists():
                    return lib_path

        return None

    def parse(self, source_code: str) -> Optional[Dict[str, Any]]:
        """Parse SAS source code and return AST.

        Args:
            source_code: SAS source code to parse

        Returns:
            Dictionary representation of the parse tree,
            or None if parsing fails.
        """
        if not self.parser:
            # Use a lightweight stub parser that recognises common top-level
            # statements so downstream stages can make better decisions and
            # emit useful diagnostics instead of operating on an empty AST.
            return self._stub_parse(source_code)

        # Use tree-sitter parsing with the compiled grammar
        try:
            tree = self.parser.parse(source_code.encode())
            return self._tree_to_dict(tree.root_node)
        except Exception as e:
            warnings.warn(
                f"Parsing with Tree-sitter failed: {e}. Falling back to stub parser.\n"
                f"{self._build_instructions}"
            )
            return self._stub_parse(source_code)

    def _tree_to_dict(self, node: Any) -> Dict[str, Any]:
        """Convert tree-sitter node to dictionary."""
        # tree-sitter Node.text may be bytes on some bindings; handle both
        try:
            text = node.text.decode() if isinstance(node.text, (bytes, bytearray)) else node.text
        except Exception:
            # Some tree-sitter versions don't expose `.text`; fallback to empty
            text = ""

        return {
            "type": node.type,
            "start_byte": getattr(node, "start_byte", None),
            "end_byte": getattr(node, "end_byte", None),
            "start_point": getattr(node, "start_point", None),
            "end_point": getattr(node, "end_point", None),
            "children": [self._tree_to_dict(child) for child in getattr(node, "children", [])],
            "text": text,
        }

    @staticmethod
    def _classify_statement(text: str) -> str:
        """Classify a semicolon-terminated statement by its keyword.

        Args:
            text: The statement text (should include trailing semicolon)

        Returns:
            Statement type keyword (e.g., 'proc', 'options', 'libname', etc.)
        """
        text_lower = text.strip().lower()
        # Remove leading whitespace and get first word
        first_word = text_lower.split()[0] if text_lower.split() else ""
        return first_word

    @staticmethod
    def _parse_data_step_statements(data_step_text: str) -> List[Dict[str, Any]]:
        """Parse DATA step internal statements.

        Extracts and identifies individual statements within a DATA step
        (SET, MERGE, BY, KEEP, DROP, LENGTH, FORMAT, INFORMAT, RETAIN, OUTPUT, DELETE).

        Args:
            data_step_text: Full text of a DATA step block

        Returns:
            List of statement nodes with their types
        """
        children: List[Dict[str, Any]] = []

        # Remove the 'data ... ;' header and 'run;' footer
        flags = re.IGNORECASE | re.DOTALL
        # Remove data declaration
        content = re.sub(r"^\s*data\b[^;]*;", "", data_step_text, flags=flags)
        # Remove run/quit
        content = re.sub(r"\b(?:run|quit)\s*;\s*$", "", content, flags=flags)

        # Define patterns for DATA step statements
        statement_patterns = [
            (r"\bset\b[^;]*;", "set_statement"),
            (r"\bmerge\b[^;]*;", "merge_statement"),
            (r"\bby\b[^;]*;", "by_statement"),
            (r"\bkeep\b[^;]*;", "keep_statement"),
            (r"\bdrop\b[^;]*;", "drop_statement"),
            (r"\blength\b[^;]*;", "length_statement"),
            (r"\bformat\b[^;]*;", "format_statement"),
            (r"\binformat\b[^;]*;", "informat_statement"),
            (r"\bretain\b[^;]*;", "retain_statement"),
            (r"\boutput\b[^;]*;", "output_statement"),
            (r"\bdelete\s*;", "delete_statement"),
        ]

        pos = 0
        content_len = len(content)

        while pos < content_len:
            # Find the next statement match
            earliest_match = None
            earliest_type = None
            earliest_end = content_len

            for pattern, stmt_type in statement_patterns:
                match = re.search(pattern, content[pos:], flags)
                if match:
                    match_start = pos + match.start()
                    match_end = pos + match.end()
                    if match_start < earliest_end:
                        earliest_match = match
                        earliest_type = stmt_type
                        earliest_end = match_end

            if earliest_match:
                match_text = content[
                    pos + earliest_match.start() : pos + earliest_match.end()
                ].strip()
                if match_text:
                    children.append(
                        {
                            "type": earliest_type,
                            "text": match_text,
                            "children": [],
                        }
                    )
                pos = pos + earliest_match.end()
            else:
                # Skip to next semicolon to find unparsed statements
                next_semi = content.find(";", pos)
                if next_semi > pos:
                    unparsed = content[pos : next_semi + 1].strip()
                    if unparsed and unparsed != ";":
                        # Check if it looks like an assignment, if, do, or other supported statement
                        if "=" in unparsed and not re.match(r"^\w+\s*;$", unparsed):
                            children.append(
                                {
                                    "type": "assignment_statement",
                                    "text": unparsed,
                                    "children": [],
                                }
                            )
                        elif re.match(r"^\s*if\b", unparsed, flags):
                            children.append(
                                {
                                    "type": "if_statement",
                                    "text": unparsed,
                                    "children": [],
                                }
                            )
                        elif re.match(r"^\s*do\b", unparsed, flags):
                            children.append(
                                {
                                    "type": "do_loop",
                                    "text": unparsed,
                                    "children": [],
                                }
                            )
                        else:
                            children.append(
                                {
                                    "type": "other_statement",
                                    "text": unparsed,
                                    "children": [],
                                }
                            )
                    pos = next_semi + 1
                else:
                    break

        return children

    def _stub_parse(self, source: str) -> Dict[str, Any]:
        """Lightweight heuristic parser for top-level statements.

        Produces a dictionary AST with child nodes for common top-level
        constructs. This is intentionally conservative and intended to be
        used only when the compiled grammar is unavailable.
        """
        s = source or ""
        children: List[Dict[str, Any]] = []

        # Compile patterns used to recognise statement types. The patterns
        # are intentionally permissive; they aim to capture common top-level
        # blocks and single-line statements.
        flags = re.IGNORECASE | re.DOTALL
        data_pat = re.compile(r"\bdata\b.*?\brun\s*;", flags)
        proc_pat = re.compile(r"\bproc\b.*?\b(?:run|quit)\s*;", flags)
        libname_pat = re.compile(r"\blibname\b[^;]*;", flags)
        options_pat = re.compile(r"\boptions\b[^;]*;", flags)
        stmt_pat = re.compile(r"[^;]+;", re.DOTALL)

        pos = 0
        length = len(s)

        # Helper to append stmt from span
        def append_node(
            node_type: str, start: int, end: int, inner_children: Optional[List] = None
        ) -> None:
            text = s[start:end].strip()
            if not text:
                return
            children.append(
                {
                    "type": node_type,
                    "start_byte": start,
                    "end_byte": end,
                    "children": inner_children if inner_children is not None else [],
                    "text": text,
                }
            )

        # Walk through the source and pick the earliest special match
        while pos < length:
            # Find next match among special patterns
            candidates = []
            for pat, ntype in (
                (data_pat, "data_step"),
                (proc_pat, "proc_step"),
                (libname_pat, "libname_statement"),
                (options_pat, "options_statement"),
            ):
                m = pat.search(s, pos)
                if m:
                    candidates.append((m.start(), m.end(), ntype, m))

            if candidates:
                # pick nearest match
                candidates.sort(key=lambda t: t[0])
                start, end, ntype, match = candidates[0]

                # Any intermediate simple statements before the special block?
                if start > pos:
                    for sm in stmt_pat.finditer(s, pos, start):
                        stmt_text = s[sm.start() : sm.end()].strip()
                        stmt_type = self._classify_statement(stmt_text)
                        append_node(stmt_type, sm.start(), sm.end())

                # For DATA steps, parse internal statements
                if ntype == "data_step":
                    data_step_children = self._parse_data_step_statements(s[start:end])
                    append_node(ntype, start, end, data_step_children)
                else:
                    append_node(ntype, start, end)

                pos = end
                continue

            # No special block ahead — append remaining semicolon-terminated statements
            appended = False
            for sm in stmt_pat.finditer(s, pos):
                stmt_text = s[sm.start() : sm.end()].strip()
                stmt_type = self._classify_statement(stmt_text)
                append_node(stmt_type, sm.start(), sm.end())
                pos = sm.end()
                appended = True

            if not appended:
                break

        return {"type": "source_file", "children": children, "text": s}

    def parse_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a SAS file and return AST."""
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
        return self.parse(source_code)


class ASTNode:
    """Represents a node in the AST."""

    def __init__(self, node_type: str, text: str = "", **metadata: Any):
        self.node_type = node_type
        self.text = text
        self.children: List["ASTNode"] = []
        self.metadata = metadata

    def add_child(self, child: "ASTNode") -> None:
        """Add a child node."""
        self.children.append(child)

    def __repr__(self) -> str:
        return f"ASTNode(type={self.node_type}, children={len(self.children)})"


class ASTBuilder:
    """Builds typed AST from tree-sitter output."""

    @staticmethod
    def build_from_dict(ast_dict: Dict[str, Any]) -> ASTNode:
        """Build typed AST from dictionary representation."""
        node = ASTNode(
            node_type=ast_dict.get("type", "unknown"),
            text=ast_dict.get("text", ""),
            **{k: v for k, v in ast_dict.items() if k not in ("type", "text", "children")},
        )

        for child_dict in ast_dict.get("children", []):
            child = ASTBuilder.build_from_dict(child_dict)
            node.add_child(child)

        return node

    @staticmethod
    def find_nodes(node: ASTNode, node_type: str) -> List[ASTNode]:
        """Find all nodes of a specific type."""
        results: List[ASTNode] = []
        if node.node_type == node_type:
            results.append(node)
        for child in node.children:
            results.extend(ASTBuilder.find_nodes(child, node_type))
        return results
