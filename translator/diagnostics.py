"""
Diagnostic reporting for IF/ELSE handling and other translation issues.

Provides a centralized way to track and report various categories of diagnostics:
- Orphan ELSE statements (semantic errors)
- Unsupported IF consequence types
- IF statements with mixed-column assignments
- Unsupported top-level statements (PROC, OPTIONS, LIBNAME, etc.)
- Other translation warnings
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class DiagnosticSeverity(Enum):
    """Severity levels for diagnostics."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DiagnosticCategory(Enum):
    """Categories of diagnostics."""

    ORPHAN_ELSE = "orphan_else"
    UNSUPPORTED_CONSEQUENCE = "unsupported_consequence"
    MIXED_COLUMN_ASSIGNMENT = "mixed_column_assignment"
    CONDITIONAL_OUTPUT = "conditional_output"
    CONDITIONAL_DELETE = "conditional_delete"
    DO_BLOCK_CONDITIONAL = "do_block_conditional"
    UNPARSEABLE_CONDITIONAL = "unparseable_conditional"
    UNSUPPORTED_TOP_LEVEL = "unsupported_top_level"
    UNPARSED_TOKENS = "unparsed_tokens"
    MULTIPLE_DATA_STEPS = "multiple_data_steps"
    MULTIPLE_DATASETS = "multiple_datasets"
    UNSUPPORTED_STATEMENT = "unsupported_statement"
    OTHER = "other"


@dataclass
class Diagnostic:
    """Represents a single diagnostic message."""

    severity: DiagnosticSeverity
    category: DiagnosticCategory
    message: str
    location: Optional[str] = None  # e.g., "line 42", "data_step_1"
    source_text: Optional[str] = None  # The actual SAS code snippet
    suggestion: Optional[str] = None  # Recommended fix or workaround


@dataclass
class DiagnosticReport:
    """Report of all diagnostics from translation."""

    diagnostics: List[Diagnostic] = field(default_factory=list)
    by_category: Dict[DiagnosticCategory, List[Diagnostic]] = field(default_factory=dict)
    summary: Dict[str, int] = field(default_factory=dict)

    def add(
        self,
        severity: DiagnosticSeverity,
        category: DiagnosticCategory,
        message: str,
        location: Optional[str] = None,
        source_text: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add a diagnostic to the report.

        Args:
            severity: Severity level
            category: Diagnostic category
            message: Description of the issue
            location: Location in source (optional)
            source_text: The problematic SAS code (optional)
            suggestion: Recommended fix (optional)
        """
        diag = Diagnostic(
            severity=severity,
            category=category,
            message=message,
            location=location,
            source_text=source_text,
            suggestion=suggestion,
        )
        self.diagnostics.append(diag)

        if category not in self.by_category:
            self.by_category[category] = []
        self.by_category[category].append(diag)

        # Update summary
        key = f"{severity.value}_{category.value}"
        self.summary[key] = self.summary.get(key, 0) + 1

    def add_orphan_else(self, source_text: str, location: Optional[str] = None) -> None:
        """Add diagnostic for ELSE without preceding IF.

        Args:
            source_text: The ELSE statement
            location: Location in source (optional)
        """
        self.add(
            severity=DiagnosticSeverity.ERROR,
            category=DiagnosticCategory.ORPHAN_ELSE,
            message="ELSE without preceding IF - this is a semantic error in SAS",
            location=location,
            source_text=source_text,
            suggestion="Ensure all ELSE clauses are preceded by IF/THEN",
        )

    def add_mixed_column_assignment(
        self, columns: List[str], source_text: Optional[str] = None, location: Optional[str] = None
    ) -> None:
        """Add diagnostic for IF assigning to multiple different columns.

        Args:
            columns: List of column names being assigned
            source_text: The IF statement (optional)
            location: Location in source (optional)
        """
        cols_str = ", ".join(columns)
        self.add(
            severity=DiagnosticSeverity.WARNING,
            category=DiagnosticCategory.MIXED_COLUMN_ASSIGNMENT,
            message=f"IF/ELSE assigns to multiple different columns: {cols_str}",
            location=location,
            source_text=source_text,
            suggestion="Consider restructuring to assign to a single computed column, or split into separate DATA steps",
        )

    def add_conditional_output(
        self, condition: str, source_text: Optional[str] = None, location: Optional[str] = None
    ) -> None:
        """Add diagnostic for IF with OUTPUT consequence.

        Args:
            condition: The IF condition
            source_text: The IF statement (optional)
            location: Location in source (optional)
        """
        self.add(
            severity=DiagnosticSeverity.WARNING,
            category=DiagnosticCategory.CONDITIONAL_OUTPUT,
            message=f"IF statement with OUTPUT consequence (condition: {condition})",
            location=location,
            source_text=source_text,
            suggestion="OUTPUT in conditionals requires careful handling; consider restructuring to use separate DATA steps",
        )

    def add_conditional_delete(
        self, condition: str, source_text: Optional[str] = None, location: Optional[str] = None
    ) -> None:
        """Add diagnostic for IF with DELETE consequence.

        Args:
            condition: The IF condition
            source_text: The IF statement (optional)
            location: Location in source (optional)
        """
        self.add(
            severity=DiagnosticSeverity.WARNING,
            category=DiagnosticCategory.CONDITIONAL_DELETE,
            message=f"IF statement with DELETE consequence (condition: {condition})",
            location=location,
            source_text=source_text,
            suggestion="DELETE in conditionals will be converted to WHERE filtering",
        )

    def add_do_block_conditional(
        self, source_text: Optional[str] = None, location: Optional[str] = None
    ) -> None:
        """Add diagnostic for IF with DO...END block.

        Args:
            source_text: The IF statement (optional)
            location: Location in source (optional)
        """
        self.add(
            severity=DiagnosticSeverity.WARNING,
            category=DiagnosticCategory.DO_BLOCK_CONDITIONAL,
            message="IF statement with DO...END block requires nested statement parsing",
            location=location,
            source_text=source_text,
            suggestion="This is not yet fully supported; consider simplifying the logic",
        )

    def add_unsupported_top_level_statement(
        self, statement_type: str, source_text: Optional[str] = None, location: Optional[str] = None
    ) -> None:
        """Add diagnostic for unsupported top-level statement.

        Args:
            statement_type: The type of statement (e.g., 'PROC', 'OPTIONS', 'LIBNAME')
            source_text: The statement (optional)
            location: Location in source (optional)
        """
        self.add(
            severity=DiagnosticSeverity.WARNING,
            category=DiagnosticCategory.UNSUPPORTED_TOP_LEVEL,
            message=f"{statement_type.upper()} statement is not yet supported in translation",
            location=location,
            source_text=source_text,
            suggestion=f"This {statement_type.upper()} statement will be skipped during code generation",
        )

    def add_unparsed_top_level_statement(
        self, source_text: Optional[str] = None, location: Optional[str] = None
    ) -> None:
        """Add diagnostic for unparsed top-level statement.

        Args:
            source_text: The statement (optional)
            location: Location in source (optional)
        """
        self.add(
            severity=DiagnosticSeverity.WARNING,
            category=DiagnosticCategory.UNSUPPORTED_TOP_LEVEL,
            message="Top-level statement could not be parsed or is not recognized",
            location=location,
            source_text=source_text,
            suggestion="Check the syntax of this statement; it will be skipped",
        )

    def get_errors(self) -> List[Diagnostic]:
        """Get all error-level diagnostics."""
        return [d for d in self.diagnostics if d.severity == DiagnosticSeverity.ERROR]

    def get_warnings(self) -> List[Diagnostic]:
        """Get all warning-level diagnostics."""
        return [d for d in self.diagnostics if d.severity == DiagnosticSeverity.WARNING]

    def get_by_category(self, category: DiagnosticCategory) -> List[Diagnostic]:
        """Get all diagnostics for a specific category."""
        return self.by_category.get(category, [])

    def format_summary(self) -> str:
        """Format a text summary of all diagnostics."""
        lines = ["=== Translation Diagnostics ===", ""]

        # Summary counts
        errors = len(self.get_errors())
        warnings = len(self.get_warnings())
        total = len(self.diagnostics)

        lines.append(f"Total: {total} diagnostics ({errors} errors, {warnings} warnings)")
        lines.append("")

        # By category
        if self.by_category:
            lines.append("By Category:")
            for category in sorted(self.by_category.keys(), key=lambda c: c.value):
                diags = self.by_category[category]
                lines.append(f"  {category.value}: {len(diags)}")

        return "\n".join(lines)

    def format_detailed(self) -> str:
        """Format detailed report of all diagnostics."""
        lines = [self.format_summary(), ""]

        # Errors
        errors = self.get_errors()
        if errors:
            lines.append("ERRORS:")
            for diag in errors:
                lines.append(f"  [{diag.category.value}] {diag.message}")
                if diag.location:
                    lines.append(f"    Location: {diag.location}")
                if diag.source_text:
                    lines.append(f"    Source: {diag.source_text[:100]}...")
                if diag.suggestion:
                    lines.append(f"    Suggestion: {diag.suggestion}")
            lines.append("")

        # Warnings
        warnings = self.get_warnings()
        if warnings:
            lines.append("WARNINGS:")
            for diag in warnings:
                lines.append(f"  [{diag.category.value}] {diag.message}")
                if diag.location:
                    lines.append(f"    Location: {diag.location}")
                if diag.source_text:
                    lines.append(f"    Source: {diag.source_text[:100]}...")
                if diag.suggestion:
                    lines.append(f"    Suggestion: {diag.suggestion}")

        return "\n".join(lines)


# Global diagnostic report (for use during translation)
_global_diagnostics = DiagnosticReport()


def get_global_diagnostics() -> DiagnosticReport:
    """Get the global diagnostic report."""
    return _global_diagnostics


def reset_diagnostics() -> None:
    """Reset the global diagnostic report."""
    global _global_diagnostics
    _global_diagnostics = DiagnosticReport()
