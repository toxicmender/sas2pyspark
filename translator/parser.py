"""
"""Parser layer using tree-sitter for SAS syntax parsing.

Provides parsing and AST construction for SAS source code.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import warnings


class SASParser:
    """Wrapper around tree-sitter SAS parser."""

    def __init__(self):
        """Initialize the SAS parser.

        Attempts to load the compiled Tree-sitter SAS grammar.
        Falls back to stub parser if grammar is not available.
        """
        self.parser = None
        self.language = None
        self.grammar_loaded = False

        try:
            from tree_sitter import Language, Parser

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
                        f"Failed to load compiled Tree-sitter grammar: {e}. "
                        f"Using stub parser. To use full grammar, run: "
                        f"python scripts/build-grammar.py"
                    )
            else:
                warnings.warn(
                    "Tree-sitter SAS grammar not compiled. Using stub parser. "
                    "To build the grammar, run: python scripts/build-grammar.py"
                )
        except ImportError:
            warnings.warn(
                "tree-sitter library not installed. Using stub parser. "
                "Install with: pip install tree-sitter"
            )

    @staticmethod
    def _find_compiled_grammar() -> Optional[Path]:
        """Find the compiled Tree-sitter grammar library.

        Searches in common locations for the compiled grammar binary.
        Tree-sitter generates platform-specific binaries.
        """
        # Check in tree-sitter-sas directory
        project_root = Path(__file__).parent.parent
        grammar_dir = project_root / "tree-sitter-sas"

        # Try to find the compiled library
        # On Windows: .dll, on macOS: .dylib, on Linux: .so
        possible_names = [
            f"sas.{ext}"
            for ext in ["dll", "so", "dylib"]
        ]

        # Check build directory
        build_dir = grammar_dir / "build" / "Release"
        for name in possible_names:
            lib_path = build_dir / name
            if lib_path.exists():
                return lib_path

        # Tree-sitter may also place it in build/Release or similar
        for subdir in ["build/Release", "build", "src"]:
            potential_dir = grammar_dir / subdir
            if potential_dir.exists():
                for name in possible_names:
                    lib_path = potential_dir / name
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
            # Return a stub AST for demonstration
            # This allows the translator to work even without the grammar
            return {
                "type": "source_file",
                "children": [],
                "text": source_code,
            }

        # Use tree-sitter parsing with the compiled grammar
        try:
            tree = self.parser.parse(source_code.encode())
            return self._tree_to_dict(tree.root_node)
        except Exception as e:
            warnings.warn(f"Parsing failed: {e}")
            return {
                "type": "source_file",
                "children": [],
                "text": source_code,
            }

    def _tree_to_dict(self, node: Any) -> Dict[str, Any]:
        """Convert tree-sitter node to dictionary."""
        return {
            "type": node.type,
            "start_byte": node.start_byte,
            "end_byte": node.end_byte,
            "start_point": node.start_point,
            "end_point": node.end_point,
            "children": [self._tree_to_dict(child) for child in node.children],
            "text": node.text.decode() if isinstance(node.text, bytes) else node.text,
        }

    def parse_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a SAS file and return AST."""
        with open(file_path, "r") as f:
            source_code = f.read()
        return self.parse(source_code)


class ASTNode:
    """Represents a node in the AST."""

    def __init__(self, node_type: str, text: str = "", **metadata: Any):
        self.node_type = node_type
        self.text = text
        self.children: List[ASTNode] = []
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
        )

        for child_dict in ast_dict.get("children", []):
            child = ASTBuilder.build_from_dict(child_dict)
            node.add_child(child)

        return node

    @staticmethod
    def find_nodes(node: ASTNode, node_type: str) -> List[ASTNode]:
        """Find all nodes of a specific type."""
        results = []
        if node.node_type == node_type:
            results.append(node)
        for child in node.children:
            results.extend(ASTBuilder.find_nodes(child, node_type))
        return results
