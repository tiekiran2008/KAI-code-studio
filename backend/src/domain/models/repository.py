from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class CodeSymbol:
    name: str
    symbol_type: str  # class, function, method, interface, enum, variable
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    complexity: int = 0
    dependencies: List[str] = field(default_factory=list)

@dataclass
class SourceFile:
    path: str
    language: str
    content: str
    symbols: List[CodeSymbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)

@dataclass
class Repository:
    id: str
    url: str
    name: str
    branch: str
    files: List[SourceFile] = field(default_factory=list)
