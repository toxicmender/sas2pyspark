"""
Semantic analysis layer for SAS to PySpark translation.

Responsible for:
- Dataset lineage tracking
- Variable scope resolution
- DATA step execution semantics
- BY-group processing
- RETAIN behavior
- Macro expansion
- Implicit output handling
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class VariableScope(Enum):
    """Variable scope types."""

    GLOBAL = "global"
    DATA_STEP = "data_step"
    PROC_STEP = "proc_step"
    MACRO = "macro"


class VariableType(Enum):
    """Variable types in SAS."""

    NUMERIC = "numeric"
    CHARACTER = "character"
    AUTOMATIC = "automatic"
    RETAINED = "retained"


@dataclass
class Variable:
    """Represents a SAS variable."""

    name: str
    var_type: VariableType
    scope: VariableScope
    initial_value: Optional[Any] = None
    format_spec: Optional[str] = None
    informat_spec: Optional[str] = None
    length: Optional[int] = None


@dataclass
class DatasetMetadata:
    """Metadata about a dataset."""

    name: str
    variables: Dict[str, Variable] = field(default_factory=dict)
    observations: Optional[int] = None
    created_by: Optional[str] = None
    source: Optional[str] = None  # Source dataset name if derived

    def add_variable(self, variable: Variable) -> None:
        """Add a variable to the dataset."""
        self.variables[variable.name] = variable

    def get_variables(self) -> List[str]:
        """Get list of variable names."""
        return list(self.variables.keys())


@dataclass
class SemanticContext:
    """Context for semantic analysis."""

    datasets: Dict[str, DatasetMetadata] = field(default_factory=dict)
    variables: Dict[str, Variable] = field(default_factory=dict)
    retained_variables: Set[str] = field(default_factory=set)
    by_variables: List[str] = field(default_factory=list)
    automatic_variables: Set[str] = field(default_factory=set)

    # Library/catalog mappings
    library_mappings: Dict[str, str] = field(default_factory=dict)

    # Macro context
    macro_variables: Dict[str, str] = field(default_factory=dict)

    # Current scope
    current_scope: VariableScope = VariableScope.GLOBAL

    def declare_dataset(self, name: str) -> DatasetMetadata:
        """Declare a new dataset."""
        metadata = DatasetMetadata(name=name)
        self.datasets[name] = metadata
        return metadata

    def get_dataset(self, name: str) -> Optional[DatasetMetadata]:
        """Get dataset metadata."""
        return self.datasets.get(name)

    def declare_variable(self, name: str, var_type: VariableType) -> Variable:
        """Declare a variable."""
        var = Variable(name=name, var_type=var_type, scope=self.current_scope)
        self.variables[name] = var
        return var

    def mark_retained(self, name: str) -> None:
        """Mark a variable as retained."""
        self.retained_variables.add(name)
        if name in self.variables:
            self.variables[name].var_type = VariableType.RETAINED

    def set_by_variables(self, variables: List[str]) -> None:
        """Set BY variables for current processing."""
        self.by_variables = variables

    def is_automatic(self, name: str) -> bool:
        """Check if variable is automatic (e.g., _N_, _ERROR_)."""
        return name in self.automatic_variables or name.startswith("_")


class SemanticAnalyzer:
    """Performs semantic analysis on SAS AST."""

    def __init__(self, context: Optional[SemanticContext] = None):
        self.context = context or SemanticContext()
        self._initialize_automatic_variables()

    def _initialize_automatic_variables(self) -> None:
        """Initialize SAS automatic variables."""
        automatic_vars = [
            "_N_",  # Observation number
            "_ERROR_",  # Error flag
            "_CHARACTER_",  # Character variable count
            "_NUMERIC_",  # Numeric variable count
        ]
        self.context.automatic_variables.update(automatic_vars)

    def analyze_data_step(self, dataset_name: str) -> None:
        """Analyze a DATA step."""
        self.context.current_scope = VariableScope.DATA_STEP
        self.context.declare_dataset(dataset_name)

    def analyze_proc_step(self, proc_name: str) -> None:
        """Analyze a PROC step."""
        self.context.current_scope = VariableScope.PROC_STEP

    def analyze_set_statement(self, dataset_names: List[str]) -> None:
        """Analyze a SET statement and inherit variables."""
        for dataset_name in dataset_names:
            source_metadata = self.context.get_dataset(dataset_name)
            if source_metadata:
                # Inherit variables from source dataset
                for var_name, variable in source_metadata.variables.items():
                    self.context.variables[var_name] = variable

    def analyze_merge_statement(self, dataset_names: List[str]) -> None:
        """Analyze a MERGE statement."""
        for dataset_name in dataset_names:
            source_metadata = self.context.get_dataset(dataset_name)
            if source_metadata:
                # Inherit variables from source datasets
                for var_name, variable in source_metadata.variables.items():
                    self.context.variables[var_name] = variable

    def analyze_by_statement(self, variables: List[str]) -> None:
        """Analyze a BY statement."""
        self.context.set_by_variables(variables)

    def get_variable_lineage(self, var_name: str) -> Optional[Variable]:
        """Get variable definition and its lineage."""
        return self.context.variables.get(var_name)

    def get_dataset_dependencies(self, dataset_name: str) -> Set[str]:
        """Get input datasets that a dataset depends on."""
        dependencies = set()
        metadata = self.context.get_dataset(dataset_name)
        if metadata and metadata.source:
            dependencies.add(metadata.source)
        return dependencies

    def get_context(self) -> SemanticContext:
        """Get the semantic context."""
        return self.context
