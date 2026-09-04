"""
RAG Domain Models
=================
Core data transfer objects for the RAG pipeline. These are pure Python
dataclasses with no external dependencies, following Clean Architecture
principles (Domain layer has zero infrastructure imports).
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


# ---------------------------------------------------------------------------
# Query Intent
# ---------------------------------------------------------------------------

class QueryIntent(str, Enum):
    """Classifies the user's intent so the pipeline can apply the correct
    prompt template and retrieval strategy."""
    EXPLAIN_CODE = "explain_code"
    FIND_IMPLEMENTATION = "find_implementation"
    DEBUG_ISSUE = "debug_issue"
    ARCHITECTURE = "architecture"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    API_EXPLANATION = "api_explanation"
    SECURITY_REVIEW = "security_review"
    PERFORMANCE_REVIEW = "performance_review"
    DOCUMENTATION = "documentation"
    GENERAL_SEARCH = "general_search"


# ---------------------------------------------------------------------------
# Query Models
# ---------------------------------------------------------------------------

@dataclass
class ParsedQuery:
    """Output of QueryUnderstanding + QueryRewriter stages."""
    original_query: str
    rewritten_queries: List[str]          # 1..N expanded sub-queries
    intent: QueryIntent
    detected_symbols: List[str] = field(default_factory=list)   # CamelCase / snake_case names
    detected_files: List[str] = field(default_factory=list)     # e.g. "auth.py"
    language_hints: List[str] = field(default_factory=list)     # e.g. ["python", "typescript"]
    repo_id: str = ""
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Retrieval Models
# ---------------------------------------------------------------------------

@dataclass
class RerankedChunk:
    """A retrieved chunk enriched with all re-ranking signal scores."""
    chunk_id: str
    repo_id: str
    file_path: str
    content: str
    language: str
    commit_hash: str
    symbol_name: Optional[str]
    symbol_type: Optional[str]
    start_line: Optional[int]
    end_line: Optional[int]
    imports: List[str] = field(default_factory=list)

    # Scoring signals
    embedding_score: float = 0.0
    symbol_importance_score: float = 0.0
    structure_score: float = 0.0
    file_relevance_score: float = 0.0
    dependency_score: float = 0.0
    metadata_score: float = 0.0

    @property
    def final_score(self) -> float:
        """Weighted composite score for ranking."""
        return (
            self.embedding_score        * 0.35 +
            self.symbol_importance_score * 0.20 +
            self.structure_score        * 0.15 +
            self.file_relevance_score   * 0.15 +
            self.dependency_score       * 0.10 +
            self.metadata_score         * 0.05
        )


# ---------------------------------------------------------------------------
# Context Window
# ---------------------------------------------------------------------------

@dataclass
class ContextWindow:
    """Deduplicated, token-budgeted context ready for the prompt builder."""
    chunks: List[RerankedChunk]
    total_tokens: int
    formatted_context: str                # Pre-formatted string for prompt injection
    file_map: Dict[str, List[RerankedChunk]] = field(default_factory=dict)
    token_budget: int = 12_000
    truncated: bool = False


# ---------------------------------------------------------------------------
# Citation Models
# ---------------------------------------------------------------------------

@dataclass
class Citation:
    """Source attribution for a fact in the RAG response."""
    file_path: str
    repo_path: str
    class_name: Optional[str]
    function_name: Optional[str]
    start_line: Optional[int]
    end_line: Optional[int]
    symbol_type: Optional[str]
    confidence: float                     # 0.0 – 1.0
    chunk_id: str                         # Back-reference to retrieved chunk


# ---------------------------------------------------------------------------
# LLM Models
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """Raw response from any LLM provider."""
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_name: str
    finish_reason: str = "stop"
    raw_response: Optional[Any] = None


# ---------------------------------------------------------------------------
# Response Validation
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Output of the ResponseValidator stage."""
    is_valid: bool
    confidence: float                     # 0.0 – 1.0
    grounded_claims: int
    total_claims: int
    ungrounded_claims: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None

    @property
    def groundedness_ratio(self) -> float:
        if self.total_claims == 0:
            return 1.0
        return self.grounded_claims / self.total_claims


# ---------------------------------------------------------------------------
# RAG Response
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class RAGResponse:
    """Final structured response returned to the API layer."""
    answer: str
    citations: List[Citation]
    confidence: float
    intent: QueryIntent
    session_id: str
    repo_id: str
    latency_ms: float
    token_usage: TokenUsage
    retrieved_chunk_count: int
    is_cached: bool = False
    validation: Optional[ValidationResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

class ConversationRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ConversationTurn:
    role: ConversationRole
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationHistory:
    session_id: str
    repo_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

@dataclass
class EvaluationMetrics:
    """Evaluation results for a single RAG query."""
    query: str
    retrieval_precision: float           # Relevant retrieved / total retrieved
    retrieval_recall: float              # Relevant retrieved / total relevant
    answer_relevance: float              # 0.0 – 1.0 heuristic score
    groundedness: float                  # Claims backed by evidence / total claims
    latency_ms: float
    num_retrieved: int
    intent: QueryIntent
    session_id: str = ""
    notes: str = ""
