"""
RAG API Endpoints
=================
FastAPI router exposing the RAG pipeline through a clean HTTP interface.

Endpoints:
    POST   /api/v1/rag/query
    GET    /api/v1/rag/sessions/{session_id}
    DELETE /api/v1/rag/sessions/{session_id}
    POST   /api/v1/rag/evaluate

All endpoints are async and return structured JSON responses.
LLM unavailability is surfaced as HTTP 503.
Low-confidence answers are returned with a warning rather than an error,
as the client may want to display them with a disclaimer.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.use_cases.rag_query import RAGQueryUseCase
from src.application.use_cases.evaluate_rag import EvaluateRAGUseCase, EvaluationDataPoint
from src.application.rag.conversation_manager import ConversationManager
from src.interfaces.api.dependencies import get_rag_use_case, get_conversation_manager, get_evaluate_rag_use_case
from src.interfaces.api.v1.schemas.rag import (
    QueryRequest,
    QueryResponse,
    CitationSchema,
    TokenUsageSchema,
    ValidationSchema,
    SessionResponse,
    ConversationTurnSchema,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationMetricsSchema,
)
from src.domain.models.rag import RAGResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------

def _map_response(resp: RAGResponse) -> QueryResponse:
    """Map domain RAGResponse → Pydantic QueryResponse schema."""
    citations = [
        CitationSchema(
            file_path=c.file_path,
            repo_path=c.repo_path,
            class_name=c.class_name,
            function_name=c.function_name,
            start_line=c.start_line,
            end_line=c.end_line,
            symbol_type=c.symbol_type,
            confidence=c.confidence,
            chunk_id=c.chunk_id,
        )
        for c in resp.citations
    ]

    validation_schema = None
    if resp.validation:
        v = resp.validation
        validation_schema = ValidationSchema(
            is_valid=v.is_valid,
            confidence=v.confidence,
            grounded_claims=v.grounded_claims,
            total_claims=v.total_claims,
            ungrounded_claims=v.ungrounded_claims,
            rejection_reason=v.rejection_reason,
        )

    return QueryResponse(
        answer=resp.answer,
        citations=citations,
        confidence=resp.confidence,
        intent=resp.intent.value,
        session_id=resp.session_id,
        repo_id=resp.repo_id,
        latency_ms=resp.latency_ms,
        token_usage=TokenUsageSchema(
            prompt_tokens=resp.token_usage.prompt_tokens,
            completion_tokens=resp.token_usage.completion_tokens,
            total_tokens=resp.token_usage.total_tokens,
        ),
        retrieved_chunk_count=resp.retrieved_chunk_count,
        is_cached=resp.is_cached,
        validation=validation_schema,
        metadata=resp.metadata,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a question about a repository",
    description=(
        "Executes the full RAG pipeline: query understanding → hybrid retrieval "
        "→ re-ranking → context building → LLM generation → response validation "
        "→ citation generation. Returns a grounded answer with source citations."
    ),
)
async def query_repository(
    request: QueryRequest,
    use_case: RAGQueryUseCase = Depends(get_rag_use_case),
) -> QueryResponse:
    """Main RAG query endpoint."""
    try:
        response = await use_case.execute(
            question=request.question,
            repo_id=request.repo_id,
            session_id=request.session_id,
            top_k=request.top_k,
            token_budget=request.token_budget,
        )
        return _map_response(response)

    except Exception as exc:
        # Check if it's an LLM configuration issue
        error_str = str(exc).lower()
        if any(kw in error_str for kw in ["api_key", "apikey", "not configured", "llmconfiguration"]):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM provider is not configured. Set GEMINI_API_KEY or OPENAI_API_KEY.",
            )
        logger.error("rag_query_error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG pipeline error: {str(exc)[:200]}",
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Retrieve conversation history for a session",
)
async def get_session(
    session_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> SessionResponse:
    """Fetch all conversation turns for the given session ID."""
    history = manager.get_session(session_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found or has expired",
        )
    return SessionResponse(
        session_id=history.session_id,
        repo_id=history.repo_id,
        turns=[
            ConversationTurnSchema(
                role=t.role.value,
                content=t.content,
                timestamp=t.timestamp.isoformat(),
            )
            for t in history.turns
        ],
        created_at=history.created_at.isoformat(),
        updated_at=history.updated_at.isoformat(),
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation session",
)
async def delete_session(
    session_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> None:
    """Clear a conversation session from Redis."""
    deleted = manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )


@router.post(
    "/evaluate",
    response_model=EvaluationResponse,
    summary="Run an offline RAG evaluation",
    description=(
        "Evaluates retrieval precision/recall, answer relevance, and groundedness "
        "over a provided labelled dataset. Use for quality regression testing."
    ),
)
async def evaluate_rag(
    request: EvaluationRequest,
    use_case: EvaluateRAGUseCase = Depends(get_evaluate_rag_use_case),
) -> EvaluationResponse:
    """Evaluate RAG quality over a labelled dataset."""
    dataset = [
        EvaluationDataPoint(
            question=dp.question,
            repo_id=dp.repo_id,
            expected_chunk_ids=dp.expected_chunk_ids,
        )
        for dp in request.dataset
    ]

    try:
        all_metrics = await use_case.execute(dataset)
    except Exception as exc:
        logger.error("rag_evaluation_error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(exc)[:200]}",
        )

    n = len(all_metrics)
    return EvaluationResponse(
        num_datapoints=n,
        metrics=[
            EvaluationMetricsSchema(
                query=m.query,
                retrieval_precision=m.retrieval_precision,
                retrieval_recall=m.retrieval_recall,
                answer_relevance=m.answer_relevance,
                groundedness=m.groundedness,
                latency_ms=m.latency_ms,
                num_retrieved=m.num_retrieved,
                intent=m.intent.value,
                notes=m.notes,
            )
            for m in all_metrics
        ],
        avg_precision=sum(m.retrieval_precision for m in all_metrics) / n if n else 0.0,
        avg_recall=sum(m.retrieval_recall for m in all_metrics) / n if n else 0.0,
        avg_relevance=sum(m.answer_relevance for m in all_metrics) / n if n else 0.0,
        avg_groundedness=sum(m.groundedness for m in all_metrics) / n if n else 0.0,
        avg_latency_ms=sum(m.latency_ms for m in all_metrics if m.latency_ms > 0) / n if n else 0.0,
    )
