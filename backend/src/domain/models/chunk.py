from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class SemanticChunk:
    id: str
    repo_id: str
    file_path: str
    content: str
    language: str
    commit_hash: str
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    imports: List[str] = field(default_factory=list)

@dataclass
class SearchResult:
    chunk: SemanticChunk
    vector_score: float
    metadata_score: float = 0.0
    recency_score: float = 0.0
    symbol_importance: float = 0.0
    dependency_score: float = 0.0

    @property
    def final_score(self) -> float:
        return (
            (self.vector_score * 0.6)
            + (self.symbol_importance * 0.2)
            + (self.recency_score * 0.1)
            + (self.metadata_score * 0.1)
        )
