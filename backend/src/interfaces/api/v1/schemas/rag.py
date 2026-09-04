"""
RAG API Schemas
===============
Pydantic v2 request/response models for the RAG endpoints.
All models use strict typing and include field-level documentation
for auto-generated OpenAPI specifications.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """POST /api/v1/rag/query — inbound query payload."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural-language question about the codebase",
        examples=["How does the authentication middleware work?"],
    )
    repo_id: str = Field(
        ...,
        description="UUID of the indexed repository to search",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Existing conversation session ID for follow-up questions",
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of code chunks to retrieve (overrides server default)",
    )
    token_budget: Optional[int] = Field(
        default=None,
        ge=1000,
        le=50000,
        description="Maximum tokens to include in the context window",
    )

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be blank")
        return v.strip()


class EvaluationDataPointSchema(BaseModel):
    question: str
    repo_id: str
    expected_chunk_ids: List[str] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    """POST /api/v1/rag/evaluate — trigger an offline evaluation run."""
    dataset: List[EvaluationDataPointSchema] = Field(
        ...,
        min_length=1,
        description="Labelled evaluation dataset",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TokenUsageSchema(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class CitationSchema(BaseModel):
    """A single source attribution attached to the RAG answer."""
    file_path: str = Field(description="Relative file path in the repository")
    repo_path: str = Field(description="Full repository-relative path")
    class_name: Optional[str] = Field(default=None)
    function_name: Optional[str] = Field(default=None)
    start_line: Optional[int] = Field(default=None, description="Source start line (1-indexed)")
    end_line: Optional[int] = Field(default=None, description="Source end line (1-indexed)")
    symbol_type: Optional[str] = Field(default=None, description="class | function | method | ...")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Citation confidence: 1.0=explicit, 0.75=implicit, 0.5=residual",
    )
    chunk_id: str = Field(description="Internal chunk ID for traceability")


class ValidationSchema(BaseModel):
    is_valid: bool
    confidence: float
    grounded_claims: int
    total_claims: int
    ungrounded_claims: List[str] = Field(default_factory=list)
    rejection_reason: Optional[str] = None


class QueryResponse(BaseModel):
    """Response payload returned by POST /api/v1/rag/query."""
    answer: str = Field(description="LLM-generated answer grounded in repository code")
    citations: List[CitationSchema] = Field(
        description="Structured source attributions for the answer"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Groundedness confidence score")
    intent: str = Field(description="Detected query intent (e.g. 'explain_code')")
    session_id: str = Field(description="Conversation session ID for follow-up queries")
    repo_id: str
    latency_ms: float = Field(description="End-to-end pipeline latency in milliseconds")
    token_usage: TokenUsageSchema
    retrieved_chunk_count: int
    is_cached: bool = Field(description="True if this response was served from cache")
    validation: Optional[ValidationSchema] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationTurnSchema(BaseModel):
    role: str
    content: str
    timestamp: str


class SessionResponse(BaseModel):
    """GET /api/v1/rag/sessions/{session_id} — conversation history."""
    session_id: str
    repo_id: str
    turns: List[ConversationTurnSchema]
    created_at: str
    updated_at: str


class EvaluationMetricsSchema(BaseModel):
    query: str
    retrieval_precision: float
    retrieval_recall: float
    answer_relevance: float
    groundedness: float
    latency_ms: float
    num_retrieved: int
    intent: str
    notes: str = ""


class EvaluationResponse(BaseModel):
    """POST /api/v1/rag/evaluate — evaluation run results."""
    num_datapoints: int
    metrics: List[EvaluationMetricsSchema]
    avg_precision: float
    avg_recall: float
    avg_relevance: float
    avg_groundedness: float
    avg_latency_ms: float
