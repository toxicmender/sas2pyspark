from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DiagnosticLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Diagnostic:
    level: DiagnosticLevel
    message: str
    line: Optional[int] = None
    column: Optional[int] = None

    def format(self) -> str:
        location = ""
        if self.line is not None:
            column = self.column if self.column is not None else 0
            location = f" (line {self.line}, col {column})"
        return f"{self.level.value}: {self.message}{location}"
