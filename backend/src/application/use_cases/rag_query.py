"""
RAG Query Use Case
==================
Top-level use case that wires together the QueryProcessor with persistence
for metrics logging. This is the single entry point called by the API layer.

Responsibilities:
- Delegate to QueryProcessor for the actual RAG pipeline.
- Persist per-query metrics to PostgreSQL.
- Handle LLM unavailability gracefully (503 instead of 500).
"""
import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from src.application.rag.query_processor import QueryProcessor
from src.domain.models.rag import RAGResponse
from src.infrastructure.persistence.rag_metrics_models import DBRAGQueryMetrics

logger = logging.getLogger(__name__)


class RAGQueryUseCase:
    """
    Thin orchestration use case:
      1. Calls QueryProcessor.process()
      2. Persists metrics to DB
      3. Returns RAGResponse to the API layer
    """

    def __init__(self, processor: QueryProcessor, db_session: Session) -> None:
        self._processor = processor
        self._db = db_session

    async def execute(
        self,
        question: str,
        repo_id: str,
        session_id: Optional[str] = None,
        top_k: int = None,
        token_budget: int = None,
    ) -> RAGResponse:
        """Execute the RAG pipeline and persist result metrics."""
        response = await self._processor.process(
            question=question,
            repo_id=repo_id,
            session_id=session_id,
            top_k=top_k,
            token_budget=token_budget,
        )

        # Persist metrics asynchronously (best-effort; don't fail the request)
        try:
            self._persist_metrics(question, response)
        except Exception as exc:
            logger.warning("rag_metrics_persist_failed: %s", exc)

        return response

    def _persist_metrics(self, question: str, response: RAGResponse) -> None:
        meta = response.metadata or {}
        metrics = DBRAGQueryMetrics(
            id=str(uuid.uuid4()),
            session_id=response.session_id,
            repo_id=response.repo_id,
            intent=response.intent.value,
            original_query=question[:2000],  # Truncate very long queries
            retrieval_time_ms=meta.get("retrieval_ms", 0.0),
            rerank_time_ms=meta.get("rerank_ms", 0.0),
            context_build_time_ms=meta.get("context_ms", 0.0),
            llm_time_ms=meta.get("llm_ms", 0.0),
            total_latency_ms=response.latency_ms,
            prompt_tokens=response.token_usage.prompt_tokens,
            completion_tokens=response.token_usage.completion_tokens,
            num_retrieved_docs=response.retrieved_chunk_count,
            confidence=response.confidence,
            is_cached=str(response.is_cached).lower(),
        )
        self._db.add(metrics)
        self._db.commit()
