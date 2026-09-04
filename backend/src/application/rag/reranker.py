"""
Re-Ranker
=========
Scores retrieved chunks using 6 complementary signals and produces a
final ranked list of RerankedChunk objects ready for the context builder.

Scoring Signals & Default Weights:
┌─────────────────────────────┬────────┐
│ Signal                      │ Weight │
├─────────────────────────────┼────────┤
│ Embedding similarity        │  0.35  │
│ Symbol importance           │  0.20  │
│ Repository structure        │  0.15  │
│ File relevance              │  0.15  │
│ Dependency relationship     │  0.10  │
│ Metadata (language, recency)│  0.05  │
└─────────────────────────────┴────────┘

Design decisions:
- Weights sum to 1.0 and are configurable at construction time.
- Scores are normalised to [0,1] independently per signal.
- Dependency score is a placeholder awaiting the graph builder output;
  defaults to 0.5 so it doesn't unfairly penalise un-graphed chunks.
"""
from typing import List, Dict, Optional
from dataclasses import asdict

from src.domain.interfaces.rag import IReRanker
from src.domain.models.rag import ParsedQuery, RerankedChunk
from src.domain.models.chunk import SearchResult

# Symbol importance lookup — higher is more important for retrieval
_SYMBOL_IMPORTANCE: Dict[str, float] = {
    "class": 1.0,
    "interface": 1.0,
    "function": 0.85,
    "method": 0.85,
    "module": 0.75,
    "decorator": 0.65,
    "variable": 0.50,
    "import": 0.30,
    "comment": 0.20,
}

# Repository structure importance — core source > tests > config > docs
_STRUCTURE_PATTERNS: List[tuple] = [
    ("test", 0.30),         # Test files are less relevant for understanding
    ("spec", 0.30),
    ("mock", 0.30),
    ("fixture", 0.30),
    ("__init__", 0.50),     # Init files are structural but sparse
    ("config", 0.60),
    ("migration", 0.40),
    ("readme", 0.35),
    ("doc", 0.35),
    ("example", 0.45),
]
_DEFAULT_STRUCTURE_SCORE = 0.90   # Core source files get the highest score


def _structure_score(file_path: str) -> float:
    path_lower = file_path.lower()
    for pattern, score in _STRUCTURE_PATTERNS:
        if pattern in path_lower:
            return score
    return _DEFAULT_STRUCTURE_SCORE


def _file_relevance_score(file_path: str, detected_files: List[str], detected_symbols: List[str]) -> float:
    """Boost if the file path explicitly matches a detected file or symbol hint."""
    path_lower = file_path.lower()
    # Exact file-name match
    for f in detected_files:
        if f.lower() in path_lower:
            return 1.0
    # Symbol name appears in the file path (e.g. symbol=AuthService → auth_service.py)
    for sym in detected_symbols:
        sym_lower = sym.lower().replace("_", "")
        if sym_lower in path_lower.replace("_", ""):
            return 0.80
    return 0.50   # neutral


class ReRanker(IReRanker):
    """6-signal composite re-ranker with configurable weights."""

    def __init__(
        self,
        w_embedding: float = 0.35,
        w_symbol: float = 0.20,
        w_structure: float = 0.15,
        w_file: float = 0.15,
        w_dependency: float = 0.10,
        w_metadata: float = 0.05,
    ) -> None:
        total = w_embedding + w_symbol + w_structure + w_file + w_dependency + w_metadata
        assert abs(total - 1.0) < 1e-6, f"Weights must sum to 1.0, got {total}"
        self.w_embedding = w_embedding
        self.w_symbol = w_symbol
        self.w_structure = w_structure
        self.w_file = w_file
        self.w_dependency = w_dependency
        self.w_metadata = w_metadata

    def rerank(
        self,
        results: List[SearchResult],
        parsed_query: ParsedQuery,
        top_k: int = 8,
    ) -> List[RerankedChunk]:
        """Score, sort, and slice to top_k RerankedChunk objects."""
        ranked: List[RerankedChunk] = []

        for sr in results:
            chunk = sr.chunk

            # Signal 1: embedding similarity (normalised cosine from Qdrant)
            emb_score = max(0.0, min(1.0, sr.vector_score))

            # Signal 2: symbol importance
            sym_score = _SYMBOL_IMPORTANCE.get(chunk.symbol_type or "", 0.5)

            # Signal 3: repository structure
            struct_score = _structure_score(chunk.file_path)

            # Signal 4: file relevance to the parsed query
            file_score = _file_relevance_score(
                chunk.file_path,
                parsed_query.detected_files,
                parsed_query.detected_symbols,
            )

            # Signal 5: dependency score — use existing field if populated
            dep_score = sr.dependency_score if sr.dependency_score > 0 else 0.5

            # Signal 6: metadata score (language alignment + recency)
            meta_score = self._metadata_score(chunk.language, parsed_query.language_hints)

            rc = RerankedChunk(
                chunk_id=chunk.id,
                repo_id=chunk.repo_id,
                file_path=chunk.file_path,
                content=chunk.content,
                language=chunk.language,
                commit_hash=chunk.commit_hash,
                symbol_name=chunk.symbol_name,
                symbol_type=chunk.symbol_type,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                imports=chunk.imports,
                embedding_score=emb_score,
                symbol_importance_score=sym_score,
                structure_score=struct_score,
                file_relevance_score=file_score,
                dependency_score=dep_score,
                metadata_score=meta_score,
            )
            ranked.append(rc)

        # Sort by composite weighted score descending
        ranked.sort(key=lambda x: x.final_score, reverse=True)
        return ranked[:top_k]

    def _metadata_score(self, chunk_lang: str, language_hints: List[str]) -> float:
        """
        Full score if language matches a detected hint; neutral if no hints;
        slight penalty if language actively mismatches.
        """
        if not language_hints:
            return 0.70
        if chunk_lang.lower() in [h.lower() for h in language_hints]:
            return 1.0
        return 0.40
