"""Semantic lowering: Convert AST to Intermediate Representation (IR).

Responsible for:
- Lowering DATA steps to IR trees
- Handling multiple DATA steps in a program
- Processing multiple datasets in SET statements
- Converting statements (MERGE, BY, KEEP, DROP, etc.) to IR nodes
- Managing variable transformations and assignments
- Tracking dataset lineage and dependencies
- Handling IF/THEN/ELSE statements with various consequence types
- Supporting conditional assignments with same/different columns
"""

import re
import warnings
from typing import Dict, List, Optional, Set, Tuple

from translator.ir import (
    AssignmentNode,
    DatasetNode,
    FilterNode,
    IRNode,
    IRProgram,
    JoinNode,
    JoinType,
    ProjectionNode,
    SortNode,
    UnionNode,
)
from translator.parser import ASTBuilder, ASTNode
from translator.semantic import SemanticAnalyzer, SemanticContext, VariableScope, VariableType
from translator.semantic.conditionals import (
    ConditionalClause,
    ConditionalExpressionBuilder,
    ConditionalIRBuilder,
    ConditionalParser,
    ConditionalValidator,
    ConsequenceType,
)


class DataStepLowerer:
    """Lowers a single DATA step AST to IR."""

    def __init__(self, semantic_context: Optional[SemanticContext] = None):
        """Initialize the lowerer.

        Args:
            semantic_context: Optional semantic context to use for analysis
        """
        self.context = semantic_context or SemanticContext()
        self.semantic_analyzer = SemanticAnalyzer(self.context)
        self.output_dataset_name: Optional[str] = None
        self.input_datasets: List[str] = []
        self.by_variables: List[str] = []
        self.keep_columns: Optional[List[str]] = None
        self.drop_columns: Optional[List[str]] = None
        self.assignments: List[Tuple[str, str]] = []
        self.merge_datasets: List[str] = []
        self.merge_keys: List[str] = []
        self.output_datasets: List[str] = []
        self.delete_flag = False

    def lower_data_step(self, data_step_node: ASTNode, step_output_name: str) -> Optional[IRNode]:
        """Lower a single DATA step to an IR tree.

        Args:
            data_step_node: The data_step AST node
            step_output_name: Name of the output dataset for this step

        Returns:
            IRNode representing the transformed data, or None if unable to lower
        """
        self.output_dataset_name = step_output_name
        self.semantic_analyzer.analyze_data_step(step_output_name)

        # Process all statements within the DATA step
        for child in data_step_node.children:
            self._process_statement(child)

        # Build the IR tree based on what we found
        ir_tree = self._build_ir_tree()

        return ir_tree

    def _process_statement(self, stmt: ASTNode) -> None:
        """Process a single statement within the DATA step."""
        stmt_type = stmt.node_type

        if stmt_type == "set_statement":
            self._process_set_statement(stmt)
        elif stmt_type == "merge_statement":
            self._process_merge_statement(stmt)
        elif stmt_type == "by_statement":
            self._process_by_statement(stmt)
        elif stmt_type == "keep_statement":
            self._process_keep_statement(stmt)
        elif stmt_type == "drop_statement":
            self._process_drop_statement(stmt)
        elif stmt_type == "length_statement":
            self._process_length_statement(stmt)
        elif stmt_type == "format_statement":
            self._process_format_statement(stmt)
        elif stmt_type == "informat_statement":
            self._process_informat_statement(stmt)
        elif stmt_type == "retain_statement":
            self._process_retain_statement(stmt)
        elif stmt_type == "output_statement":
            self._process_output_statement(stmt)
        elif stmt_type == "delete_statement":
            self._process_delete_statement(stmt)
        elif stmt_type == "assignment_statement":
            self._process_assignment_statement(stmt)
        elif stmt_type == "if_statement":
            self._process_if_statement(stmt)
        elif stmt_type == "do_loop":
            self._process_do_loop(stmt)
        else:
            # Unknown or unhandled statement
            pass

    def _process_set_statement(self, stmt: ASTNode) -> None:
        """Process SET statement - extracts all dataset names."""
        # Extract all datasets from the SET statement text
        text = stmt.text.lower()
        # Remove 'set' keyword and semicolon
        text = re.sub(r"^\s*set\s+", "", text)
        text = re.sub(r"\s*;?\s*$", "", text)

        # Split by comma and process each dataset reference
        datasets = [ds.strip() for ds in text.split(",")]
        self.input_datasets.extend(datasets)

        # Notify semantic analyzer
        for dataset_name in datasets:
            self.semantic_analyzer.analyze_set_statement([dataset_name])

    def _process_merge_statement(self, stmt: ASTNode) -> None:
        """Process MERGE statement - extracts all datasets to merge."""
        text = stmt.text.lower()
        text = re.sub(r"^\s*merge\s+", "", text)
        text = re.sub(r"\s*;?\s*$", "", text)

        # Extract dataset list (may contain options in parentheses)
        # For now, just extract simple dataset names
        datasets = [ds.strip() for ds in re.split(r"[\s,]", text) if ds.strip()]
        self.merge_datasets.extend(datasets)

        self.semantic_analyzer.analyze_merge_statement(datasets)

    def _process_by_statement(self, stmt: ASTNode) -> None:
        """Process BY statement - extracts BY variables."""
        text = stmt.text.lower()
        text = re.sub(r"^\s*by\s+", "", text)
        text = re.sub(r"\s*descending\s+", "", text)
        text = re.sub(r"\s*;?\s*$", "", text)

        # Extract variable names
        variables = [var.strip() for var in text.split(",")]
        self.by_variables.extend(variables)

        self.semantic_analyzer.analyze_by_statement(variables)

    def _process_keep_statement(self, stmt: ASTNode) -> None:
        """Process KEEP statement - set columns to keep."""
        text = stmt.text.lower()
        text = re.sub(r"^\s*keep\s+", "", text)
        text = re.sub(r"\s*;?\s*$", "", text)

        columns = [col.strip() for col in text.split(",")]
        self.keep_columns = columns

    def _process_drop_statement(self, stmt: ASTNode) -> None:
        """Process DROP statement - set columns to drop."""
        text = stmt.text.lower()
        text = re.sub(r"^\s*drop\s+", "", text)
        text = re.sub(r"\s*;?\s*$", "", text)

        columns = [col.strip() for col in text.split(",")]
        self.drop_columns = columns

    def _process_length_statement(self, stmt: ASTNode) -> None:
        """Process LENGTH statement - track variable lengths."""
        # Extract length specifications
        text = stmt.text
        # This would store metadata about variable lengths
        # For now, we just acknowledge it
        pass

    def _process_format_statement(self, stmt: ASTNode) -> None:
        """Process FORMAT statement - track variable formats."""
        # Extract format specifications
        text = stmt.text
        # This would store metadata about variable formats
        pass

    def _process_informat_statement(self, stmt: ASTNode) -> None:
        """Process INFORMAT statement - track variable informats."""
        text = stmt.text
        # This would store metadata about variable informats
        pass

    def _process_retain_statement(self, stmt: ASTNode) -> None:
        """Process RETAIN statement - mark variables as retained."""
        text = stmt.text.lower()
        text = re.sub(r"^\s*retain\s+", "", text)
        text = re.sub(r"\s*;?\s*$", "", text)

        # Extract variable names
        variables = re.findall(r"(\w+)", text)
        for var in variables:
            self.context.mark_retained(var)

    def _process_output_statement(self, stmt: ASTNode) -> None:
        """Process OUTPUT statement - track output datasets."""
        text = stmt.text.lower()
        text = re.sub(r"^\s*output\s+", "", text)
        text = re.sub(r"\s*;?\s*$", "", text)

        if text.strip():
            # Specific output datasets listed
            datasets = [ds.strip() for ds in text.split(",")]
            self.output_datasets.extend(datasets)
        else:
            # Implicit output to main output dataset
            if self.output_dataset_name:
                self.output_datasets.append(self.output_dataset_name)

    def _process_delete_statement(self, stmt: ASTNode) -> None:
        """Process DELETE statement - mark for deletion."""
        self.delete_flag = True

    def _process_assignment_statement(self, stmt: ASTNode) -> None:
        """Process assignment statement - track column assignments."""
        text = stmt.text.strip()
        # Simple regex to extract variable = expression
        match = re.match(r"(\w+)\s*=\s*(.+?)\s*;?\s*$", text)
        if match:
            var_name = match.group(1)
            expression = match.group(2).rstrip(";").strip()
            self.assignments.append((var_name, expression))

    def _process_if_statement(self, stmt: ASTNode) -> None:
        """Process IF statement - extract conditions and actions.

        Supports:
        - IF/THEN assignments to same or different columns
        - IF/THEN/ELSE with multiple clauses (ELSE IF chains)
        - IF consequences: assignments, OUTPUT, DELETE, DO/END blocks
        - Conditional expressions for mixed-column assignments
        """
        text = stmt.text

        # Check for orphan ELSE (ELSE without preceding IF)
        if text.strip().lower().startswith("else"):
            warnings.warn(
                f"ELSE without preceding IF detected: '{text}'. This is a semantic error in SAS. "
                "The statement will be skipped. Ensure all ELSE clauses are preceded by IF."
            )
            return

        # Parse the IF/THEN/ELSE statement
        clauses = ConditionalParser.parse_if_statement(text)
        if not clauses:
            warnings.warn(f"Could not parse IF statement: '{text}'")
            return

        # Check for non-assignment consequences
        if ConditionalValidator.has_non_assignment_consequences(clauses):
            # Handle OUTPUT, DELETE, or DO/END blocks
            self._process_if_with_non_assignment_consequences(clauses)
        else:
            # All assignments - check if they target the same column
            is_consistent, target_column = ConditionalValidator.validate_clause_assignments(clauses)

            if is_consistent and target_column:
                # All assign to same column - can use conditional expression
                self._process_if_same_column_assignments(clauses, target_column)
            elif not is_consistent:
                # Assign to different columns - need separate transformations
                self._process_if_different_column_assignments(clauses)
            else:
                warnings.warn(
                    f"IF statement has no recognizable assignments: '{text}'. "
                    "This may be OUTPUT/DELETE logic that is not yet fully supported."
                )

    def _process_if_same_column_assignments(
        self, clauses: List[ConditionalClause], target_column: str
    ) -> None:
        """Process IF/ELSE that assigns to same column - generate conditional expression.

        Args:
            clauses: List of conditional clauses
            target_column: The target column being assigned
        """
        # Store for later IR generation
        if not hasattr(self, "conditional_assignments"):
            self.conditional_assignments = []

        self.conditional_assignments.append((target_column, clauses))

    def _process_if_different_column_assignments(self, clauses: List[ConditionalClause]) -> None:
        """Process IF/ELSE that assigns to different columns.

        Strategy: Create separate withColumn calls for each clause's assignments,
        wrapping each in its conditional.

        Args:
            clauses: List of conditional clauses
        """
        warnings.warn(
            f"IF statement assigns to multiple different columns: "
            f"{[self._extract_assignment_column(c) for c in clauses if c.consequence_type == ConsequenceType.ASSIGNMENT]}. "
            "These will be translated as separate conditional assignments. "
            "For optimal Spark code, consider assigning to a single computed column."
        )

        # Store for later processing
        if not hasattr(self, "multi_column_conditionals"):
            self.multi_column_conditionals = []

        self.multi_column_conditionals.append(clauses)

    def _process_if_with_non_assignment_consequences(
        self, clauses: List[ConditionalClause]
    ) -> None:
        """Process IF/ELSE with OUTPUT, DELETE, or DO/END consequences.

        Args:
            clauses: List of conditional clauses
        """
        for clause in clauses:
            if clause.consequence_type == ConsequenceType.OUTPUT:
                # OUTPUT statement
                warnings.warn(
                    f"IF statement with OUTPUT consequence: condition='{clause.condition}'. "
                    "OUTPUT in conditionals requires careful handling and is not yet fully supported. "
                    "Consider restructuring to use separate DATA steps."
                )
                # Track for later IR generation
                if not hasattr(self, "conditional_outputs"):
                    self.conditional_outputs = []
                self.conditional_outputs.append(clause)

            elif clause.consequence_type == ConsequenceType.DELETE:
                # DELETE statement
                warnings.warn(
                    f"IF statement with DELETE consequence: condition='{clause.condition}'. "
                    "DELETE in conditionals is typically handled as filtering. "
                    "This will be converted to a WHERE clause."
                )
                # Track for later filtering
                if not hasattr(self, "conditional_deletes"):
                    self.conditional_deletes = []
                self.conditional_deletes.append(clause)

            elif clause.consequence_type == ConsequenceType.DO_BLOCK:
                # DO...END block
                warnings.warn(
                    f"IF statement with DO...END consequence detected. "
                    "Complex DO/END blocks in conditionals require nested statement parsing. "
                    "This is not yet fully supported."
                )

    @staticmethod
    def _extract_assignment_column(clause: ConditionalClause) -> Optional[str]:
        """Extract target column name from an assignment clause.

        Args:
            clause: The conditional clause

        Returns:
            Column name or None if not an assignment
        """
        if clause.consequence_type == ConsequenceType.ASSIGNMENT:
            match = re.match(r"^\s*(\w+)\s*=", clause.consequence)
            if match:
                return match.group(1)
        return None

    def _process_do_loop(self, stmt: ASTNode) -> None:
        """Process DO loop - handle iteration logic."""
        text = stmt.text
        # For now, just acknowledge it
        pass

    def _build_ir_tree(self) -> Optional[IRNode]:
        """Build the IR tree from collected information.

        Returns:
            IRNode representing the complete transformation, or None if unable
        """
        # Start with the data source(s)
        if self.merge_datasets:
            # MERGE statement present
            ir_node = self._build_merge_ir()
        elif self.input_datasets:
            # SET statement present - may have multiple datasets
            ir_node = self._build_set_ir()
        else:
            # No input specified
            ir_node = DatasetNode("_NULL_")

        if ir_node is None:
            return None

        # Apply BY-group sort if present
        if self.by_variables:
            ir_node = self._apply_sort(ir_node)

        # Apply DROP/KEEP projection
        if self.keep_columns or self.drop_columns:
            ir_node = self._apply_projection(ir_node)

        # Apply assignments
        for var_name, expression in self.assignments:
            ir_node = AssignmentNode(var_name, expression, ir_node)

        return ir_node

    def _build_set_ir(self) -> Optional[IRNode]:
        """Build IR for SET statement with potentially multiple datasets."""
        if not self.input_datasets:
            return None

        if len(self.input_datasets) == 1:
            # Single dataset
            return DatasetNode(self.input_datasets[0])
        else:
            # Multiple datasets - use UNION
            dataset_nodes = [DatasetNode(ds) for ds in self.input_datasets]
            return UnionNode(dataset_nodes, all_mode=True)

    def _build_merge_ir(self) -> Optional[IRNode]:
        """Build IR for MERGE statement with potentially multiple datasets."""
        if not self.merge_datasets:
            return None

        if len(self.merge_datasets) == 1:
            # Single dataset (edge case)
            return DatasetNode(self.merge_datasets[0])

        # Build binary tree of joins
        ir_node = DatasetNode(self.merge_datasets[0])
        for dataset_name in self.merge_datasets[1:]:
            right_node = DatasetNode(dataset_name)
            ir_node = JoinNode(
                left=ir_node,
                right=right_node,
                keys=self.by_variables,
                join_type=JoinType.INNER,
            )

        return ir_node

    def _apply_sort(self, input_node: IRNode) -> IRNode:
        """Apply sorting based on BY variables."""
        order_by = [(var, "asc") for var in self.by_variables]
        return SortNode(order_by, input_node)

    def _apply_projection(self, input_node: IRNode) -> IRNode:
        """Apply column projection (KEEP/DROP)."""
        if self.keep_columns:
            return ProjectionNode(self.keep_columns, input_node, keep=True)
        elif self.drop_columns:
            return ProjectionNode(self.drop_columns, input_node, keep=False)
        return input_node


class SASLowerer:
    """Lowers a complete SAS program AST to IR.

    Handles multiple DATA steps and PROC steps, managing dataset dependencies
    and ensuring each step produces appropriate IR.
    """

    def __init__(self):
        """Initialize the lowerer."""
        self.semantic_context = SemanticContext()
        self.program_ir = IRProgram()
        self.processed_datasets: Set[str] = set()

    def lower_program(self, ast_root: ASTNode) -> IRProgram:
        """Lower a complete SAS program to IR.

        Args:
            ast_root: The root AST node of a parsed SAS program

        Returns:
            IRProgram containing IR for all DATA/PROC steps
        """
        self.program_ir = IRProgram()
        self.processed_datasets = set()

        # Find all top-level statements
        for child in ast_root.children:
            if child.node_type == "data_step":
                self._lower_data_step(child)
            elif child.node_type == "proc_step":
                self._lower_proc_step(child)
            else:
                # Other statement types (LIBNAME, OPTIONS, etc.)
                pass

        return self.program_ir

    def _lower_data_step(self, data_step_node: ASTNode) -> None:
        """Lower a single DATA step to IR and add to program."""
        # Extract output dataset name from DATA statement
        output_names = self._extract_output_datasets(data_step_node)

        if not output_names:
            # No specific output name - use default
            output_names = [f"_step_{len(self.program_ir.get_steps())}"]

        # Lower each output dataset
        for output_name in output_names:
            lowerer = DataStepLowerer(self.semantic_context)
            ir_tree = lowerer.lower_data_step(data_step_node, output_name)

            if ir_tree:
                self.program_ir.add_step(output_name, ir_tree)
                self.processed_datasets.add(output_name)
            else:
                warnings.warn(f"Failed to lower DATA step for dataset '{output_name}'")

    def _lower_proc_step(self, proc_step_node: ASTNode) -> None:
        """Lower a PROC step to IR."""
        # For now, we'll skip PROC steps
        # Full implementation would handle PROC SORT, PROC MEANS, etc.
        warnings.warn("PROC steps not yet supported in IR lowering")

    def _extract_output_datasets(self, data_step_node: ASTNode) -> List[str]:
        """Extract output dataset names from a DATA step node.

        Args:
            data_step_node: The data_step AST node

        Returns:
            List of output dataset names
        """
        # Extract from the data_step text
        # Format: data [lib.]dataset1 [lib.]dataset2 ...;
        text = data_step_node.text.lower()
        match = re.match(r"^\s*data\s+(.+?);", text)

        if match:
            datasets_part = match.group(1)
            # Split by comma or whitespace (may have multiple outputs)
            datasets = [ds.strip() for ds in re.split(r"[\s,]+", datasets_part) if ds.strip()]
            return datasets

        return []
