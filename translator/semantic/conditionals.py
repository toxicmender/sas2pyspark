"""
Conditional statement handling for SAS to PySpark translation.

Provides support for:
- IF/THEN/ELSE statement parsing and validation
- IF consequences: assignments, OUTPUT, DELETE, DO/END blocks
- ELSE-only detection (diagnostic)
- Conditional expression generation for mixed-column assignments
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class ConsequenceType(Enum):
    """Types of IF consequences."""

    ASSIGNMENT = "assignment"
    OUTPUT = "output"
    DELETE = "delete"
    DO_BLOCK = "do_block"
    UNKNOWN = "unknown"


@dataclass
class ConditionalClause:
    """Represents a single IF/ELSE clause."""

    condition: str
    consequence: str
    consequence_type: ConsequenceType
    elif_chain: bool = False  # True if this is an ELSE IF


class ConditionalParser:
    """Parses IF/THEN/ELSE statements."""

    @staticmethod
    def parse_if_statement(text: str) -> Optional[List[ConditionalClause]]:
        """Parse IF/THEN/ELSE statement.

        Extracts condition(s) and corresponding consequence(s).

        Args:
            text: The IF statement text

        Returns:
            List of ConditionalClause objects, or None if parsing fails
        """
        text = text.strip()
        if not text.lower().startswith("if"):
            return None

        clauses = []

        # Pattern for IF condition THEN consequence or IF...DO/END blocks
        # Handles: IF (cond) THEN statement;
        #          IF (cond) THEN DO; statements; END;
        #          IF (cond) THEN statement; ELSE statement;
        #          IF (cond) THEN DO; statements; END; ELSE DO; statements; END;

        # Remove trailing semicolon
        text = text.rstrip(";")

        # Extract IF...THEN clause
        if_match = re.match(
            r"^\s*if\s*\((.+?)\)\s*then\s+(.+?)(?=\s+else|$)", text, re.IGNORECASE | re.DOTALL
        )

        if not if_match:
            return None

        condition = if_match.group(1).strip()
        consequence = ConditionalParser._clean_consequence(if_match.group(2))

        consequence_type = ConditionalParser._identify_consequence_type(consequence)
        clauses.append(
            ConditionalClause(
                condition=condition,
                consequence=consequence,
                consequence_type=consequence_type,
            )
        )

        # Extract ELSE clause(s) if present
        remaining = text[if_match.end() :].strip()
        while remaining.lower().startswith("else"):
            remaining = remaining[4:].strip()  # Remove "else"

            # Check if it's ELSE IF (elif chain)
            if remaining.lower().startswith("if"):
                # ELSE IF case
                else_if_match = re.match(
                    r"^\s*if\s*\((.+?)\)\s*then\s+(.+?)(?=\s+else|$)",
                    remaining,
                    re.IGNORECASE | re.DOTALL,
                )
                if else_if_match:
                    elif_condition = else_if_match.group(1).strip()
                    elif_consequence = ConditionalParser._clean_consequence(else_if_match.group(2))
                    elif_type = ConditionalParser._identify_consequence_type(elif_consequence)

                    clauses.append(
                        ConditionalClause(
                            condition=elif_condition,
                            consequence=elif_consequence,
                            consequence_type=elif_type,
                            elif_chain=True,
                        )
                    )

                    remaining = remaining[else_if_match.end() :].strip()
                else:
                    break
            else:
                # Simple ELSE (no condition)
                else_match = re.match(
                    r"^(.+?)(?=\s+else|$)",
                    remaining,
                    re.IGNORECASE | re.DOTALL,
                )
                if else_match:
                    else_consequence = ConditionalParser._clean_consequence(else_match.group(1))
                    else_type = ConditionalParser._identify_consequence_type(else_consequence)

                    clauses.append(
                        ConditionalClause(
                            condition="",  # No condition for ELSE
                            consequence=else_consequence,
                            consequence_type=else_type,
                            elif_chain=False,
                        )
                    )

                remaining = remaining[else_match.end() :].strip()
                if remaining.lower().startswith("else"):
                    continue
                else:
                    break

        return clauses if clauses else None

    @staticmethod
    def _clean_consequence(consequence: str) -> str:
        """Clean consequence text by removing trailing semicolons and whitespace.

        Args:
            consequence: The consequence text to clean

        Returns:
            Cleaned consequence text
        """
        return consequence.strip().rstrip(";")

    @staticmethod
    def _identify_consequence_type(consequence: str) -> ConsequenceType:
        """Identify the type of consequence statement.

        Args:
            consequence: The consequence statement text

        Returns:
            ConsequenceType enum value
        """
        consequence_lower = consequence.lower().strip()

        if consequence_lower.startswith("output"):
            return ConsequenceType.OUTPUT
        elif consequence_lower.startswith("delete"):
            return ConsequenceType.DELETE
        elif consequence_lower.startswith("do") and consequence_lower.endswith("end"):
            return ConsequenceType.DO_BLOCK
        elif "=" in consequence and not consequence_lower.startswith("if"):
            return ConsequenceType.ASSIGNMENT
        else:
            return ConsequenceType.UNKNOWN

    @staticmethod
    def detect_orphan_else(text: str) -> bool:
        """Detect ELSE without preceding IF.

        Args:
            text: Statement text to check

        Returns:
            True if ELSE is found without matching IF
        """
        text = text.strip()
        if not text.lower().startswith("else"):
            return False

        # Check if it's part of IF/ELSE (should not happen if called on isolated statement)
        return True  # If we're checking a statement that starts with ELSE, it's orphan


class ConditionalValidator:
    """Validates IF/ELSE statement semantics."""

    @staticmethod
    def validate_clause_assignments(clauses: List[ConditionalClause]) -> Tuple[bool, Optional[str]]:
        """Validate that IF/ELSE clauses assign to consistent columns.

        Args:
            clauses: List of conditional clauses

        Returns:
            Tuple of (is_consistent, assignment_column)
            - is_consistent: True if all clauses assign to same column (or are non-assignments)
            - assignment_column: The column name if consistent, None otherwise
        """
        assignment_columns = set()

        for clause in clauses:
            if clause.consequence_type == ConsequenceType.ASSIGNMENT:
                # Extract column name from assignment
                match = re.match(r"^\s*(\w+)\s*=", clause.consequence)
                if match:
                    col_name = match.group(1)
                    assignment_columns.add(col_name)

        if len(assignment_columns) > 1:
            # Multiple different columns being assigned
            return False, None
        elif len(assignment_columns) == 1:
            # Single column being assigned
            return True, list(assignment_columns)[0]
        else:
            # No assignments (all OUTPUT/DELETE/etc.)
            return True, None

    @staticmethod
    def has_non_assignment_consequences(clauses: List[ConditionalClause]) -> bool:
        """Check if any clause has non-assignment consequences.

        Args:
            clauses: List of conditional clauses

        Returns:
            True if any clause has OUTPUT, DELETE, or DO_BLOCK
        """
        for clause in clauses:
            if clause.consequence_type in (
                ConsequenceType.OUTPUT,
                ConsequenceType.DELETE,
                ConsequenceType.DO_BLOCK,
            ):
                return True
        return False


class ConditionalExpressionBuilder:
    """Builds conditional expressions for Spark.

    When all IF/ELSE branches assign to the same column with different expressions,
    this builder generates a CASE WHEN expression or when expressions for Spark.
    """

    @staticmethod
    def build_spark_expression(clauses: List[ConditionalClause]) -> Optional[str]:
        """Build a Spark CASE WHEN expression from IF/ELSE clauses.

        Works when all clauses are simple assignments to the same column.

        Args:
            clauses: List of conditional clauses (all must be ASSIGNMENT type)

        Returns:
            Spark conditional expression string, or None if not possible
        """
        # Check all are assignments
        for clause in clauses:
            if clause.consequence_type != ConsequenceType.ASSIGNMENT:
                return None

        # Extract column name and expressions
        assignment_pairs = []
        else_expression = None

        for clause in clauses:
            match = re.match(r"^\s*(\w+)\s*=\s*(.+?)\s*$", clause.consequence)
            if match:
                col_name = match.group(1)
                expression = match.group(2)

                if not assignment_pairs and clause.condition:
                    # First condition
                    assignment_pairs.append((clause.condition, expression))
                elif clause.condition:
                    # ELSE IF
                    assignment_pairs.append((clause.condition, expression))
                else:
                    # ELSE (no condition)
                    else_expression = expression

        if not assignment_pairs:
            return None

        # Build CASE WHEN expression
        spark_expr = "F.when("
        for i, (condition, expression) in enumerate(assignment_pairs):
            if i > 0:
                spark_expr += ".when("

            # Convert SAS condition to Spark/Python
            spark_condition = ConditionalExpressionBuilder._convert_condition(condition)
            spark_expr += f"{spark_condition}, F.lit({expression})"
            if i > 0:
                spark_expr += ")"

        if else_expression:
            spark_expr += f".otherwise(F.lit({else_expression}))"
        else:
            spark_expr += ".otherwise(F.lit(None))"

        spark_expr += ")"
        return spark_expr

    @staticmethod
    def _convert_condition(sas_condition: str) -> str:
        """Convert SAS condition to Spark condition.

        Simple conversion for common cases. Full implementation would be more comprehensive.

        Args:
            sas_condition: SAS condition text

        Returns:
            Spark/Python condition expression
        """
        condition = sas_condition.strip()

        # Remove outer parentheses if present
        if condition.startswith("(") and condition.endswith(")"):
            condition = condition[1:-1]

        # Simple variable comparisons (this is a stub; full implementation would be more robust)
        # For now, return as-is and let downstream handle it
        return f"(F.col('..') {condition})"  # Placeholder; needs proper parsing


class ConditionalIRBuilder:
    """Builds IR for IF/ELSE statements with various consequence types."""

    @staticmethod
    def build_if_consequence_ir(clause: ConditionalClause) -> Tuple[str, Optional[dict]]:
        """Build IR representation for an IF consequence.

        Args:
            clause: The conditional clause

        Returns:
            Tuple of (ir_type, ir_data)
            - ir_type: Type of IR node to create (assignment, output, delete, filter)
            - ir_data: Additional data needed for the IR node
        """
        if clause.consequence_type == ConsequenceType.ASSIGNMENT:
            # Parse assignment: col = expr
            match = re.match(r"^\s*(\w+)\s*=\s*(.+?)\s*$", clause.consequence)
            if match:
                col_name = match.group(1)
                expression = match.group(2)
                return (
                    "conditional_assignment",
                    {
                        "column": col_name,
                        "expression": expression,
                        "condition": clause.condition,
                    },
                )

        elif clause.consequence_type == ConsequenceType.OUTPUT:
            # OUTPUT statement
            return (
                "conditional_output",
                {
                    "condition": clause.condition,
                    "datasets": clause.consequence.replace("output", "").strip().split(),
                },
            )

        elif clause.consequence_type == ConsequenceType.DELETE:
            # DELETE statement
            return (
                "conditional_delete",
                {"condition": clause.condition},
            )

        elif clause.consequence_type == ConsequenceType.DO_BLOCK:
            # DO...END block (complex; requires further parsing)
            return (
                "conditional_do_block",
                {
                    "condition": clause.condition,
                    "statements": clause.consequence,
                },
            )

        else:
            return ("unknown", None)
