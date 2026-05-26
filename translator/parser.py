"""
Parser layer using tree-sitter for SAS syntax parsing.

Provides parsing and AST construction for SAS source code.
"""

from typing import Any, Dict, List, Optional


class SASParser:
    """Wrapper around tree-sitter SAS parser."""

    def __init__(self):
        """Initialize the SAS parser."""
        try:
            from tree_sitter import Language, Parser

            # Try to load SAS language if available
            # For now, provide a stub implementation
            self.parser = None
            self.language = None
        except ImportError:
            self.parser = None
            self.language = None

    def parse(self, source_code: str) -> Optional[Dict[str, Any]]:
        """Parse SAS source code and return AST."""
        if not self.parser:
            # Return a stub AST for demonstration
            return {
                "type": "source_file",
                "children": [],
                "text": source_code,
            }

        # This would use tree-sitter parsing when the grammar is available
        tree = self.parser.parse(source_code.encode())
        return self._tree_to_dict(tree.root_node)

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
