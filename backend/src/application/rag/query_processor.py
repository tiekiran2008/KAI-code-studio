"""
Query Processor
===============
Top-level RAG pipeline orchestrator. Coordinates all pipeline stages and
handles caching, logging, and metrics collection.

Pipeline stages (in order):
1.  QueryUnderstanding  — classify intent, extract symbols/files
2.  QueryRewriter       — expand into multiple retrieval sub-queries
3.  HybridRetriever     — parallel fan-out: semantic + symbol + file
4.  ReRanker            — 6-signal composite scoring
5.  ContextBuilder      — dedup + token-budget-aware merge
6.  PromptBuilder       — intent-specific system + user prompt
7.  LLM completion      — via ILLMProvider (Gemini / OpenAI)
8.  ResponseValidator   — groundedness check
9.  CitationGenerator   — structured source attribution
10. ConversationManager — persist session turns

Caching:
- Full RAGResponse cached in Redis for identical (query, repo_id) pairs.
- Cache TTL: settings.RAG_RESPONSE_CACHE_TTL (default: 5 minutes).
"""
import asyncio
import hashlib
import json
import logging
import time
import uuid
from typing import Optional

import redis

from src.application.rag.query_understanding import QueryUnderstanding
from src.application.rag.query_rewriter import QueryRewriter
from src.application.rag.hybrid_retriever import HybridRetriever
from src.application.rag.reranker import ReRanker
from src.application.rag.context_builder import ContextBuilder
from src.application.rag.prompt_builder import PromptBuilder
from src.application.rag.conversation_manager import ConversationManager
from src.application.rag.response_validator import ResponseValidator
from src.application.rag.citation_generator import CitationGenerator
from src.domain.interfaces.llm import ILLMProvider
from src.domain.interfaces.embedding import IEmbeddingService
from src.domain.interfaces.vector_db import IVectorDB
from src.domain.models.rag import (
    RAGResponse,
    TokenUsage,
    ConversationRole,
    ValidationResult,
)
from src.core.config import settings
from src.core.logger import logger

_CACHE_PREFIX = "rag:response:"


def _cache_key(query: str, repo_id: str) -> str:
    digest = hashlib.sha256(f"{repo_id}::{query}".encode()).hexdigest()[:16]
    return f"{_CACHE_PREFIX}{digest}"


class QueryProcessor:
    """
    Orchestrates the full RAG pipeline from raw user query to validated
    RAGResponse with citations.
    """

    def __init__(
        self,
        llm_provider: ILLMProvider,
        embedding_service: IEmbeddingService,
        vector_db: IVectorDB,
        redis_client: redis.Redis,
    ) -> None:
        self._llm = llm_provider
        self._understanding = QueryUnderstanding()
        self._rewriter = QueryRewriter()
        self._retriever = HybridRetriever(embedding_service, vector_db)
        self._reranker = ReRanker()
        self._context_builder = ContextBuilder()
        self._prompt_builder = PromptBuilder()
        self._conversation = ConversationManager(redis_client)
        self._validator = ResponseValidator()
        self._citation_gen = CitationGenerator()
        self._redis = redis_client

    async def process(
        self,
        question: str,
        repo_id: str,
        session_id: Optional[str] = None,
        top_k: int = None,
        token_budget: int = None,
    ) -> RAGResponse:
        """
        Execute the full RAG pipeline.

        Args:
            question:     User's natural-language question.
            repo_id:      Target repository identifier.
            session_id:   Optional existing session ID for conversation context.
            top_k:        Override for number of chunks after re-ranking.
            token_budget: Override for context window token limit.

        Returns:
            RAGResponse with answer, citations, confidence, and metadata.
        """
        start_time = time.perf_counter()
        top_k = top_k or settings.TOP_K_CHUNKS
        token_budget = token_budget or settings.CONTEXT_WINDOW_TOKENS

        # ── 0. Check response cache ──────────────────────────────────────
        cache_key = _cache_key(question, repo_id)
        cached_raw = await asyncio.to_thread(self._redis.get, cache_key)
        if cached_raw:
            try:
                data = json.loads(cached_raw)
                logger.info("rag_cache_hit", question=question[:80], repo_id=repo_id)
                return self._deserialise_response(data, session_id or "cached")
            except Exception:
                pass  # Cache miss on deserialisation error

        # ── 1. Query Understanding ───────────────────────────────────────
        parsed_query = self._understanding.classify_intent(question)
        parsed_query.repo_id = repo_id
        parsed_query.session_id = session_id

        logger.info(
            "rag_query_understood",
            intent=parsed_query.intent.value,
            symbols=parsed_query.detected_symbols,
            files=parsed_query.detected_files,
        )

        # ── 2. Query Rewriting ───────────────────────────────────────────
        parsed_query = self._rewriter.rewrite(parsed_query)

        # ── 3. Conversation history ──────────────────────────────────────
        history = self._conversation.get_or_create(session_id, repo_id)
        actual_session_id = history.session_id

        # ── 4. Hybrid Retrieval ──────────────────────────────────────────
        retrieval_start = time.perf_counter()
        raw_results = await self._retriever.retrieve(parsed_query, limit=settings.MAX_RETRIEVED_CHUNKS)
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

        logger.info(
            "rag_retrieval_complete",
            num_candidates=len(raw_results),
            retrieval_ms=round(retrieval_ms, 1),
        )

        # ── 5. Re-ranking ────────────────────────────────────────────────
        rerank_start = time.perf_counter()
        ranked_chunks = self._reranker.rerank(raw_results, parsed_query, top_k=top_k)
        rerank_ms = (time.perf_counter() - rerank_start) * 1000

        # ── 6. Context Building ──────────────────────────────────────────
        context_start = time.perf_counter()
        context_window = self._context_builder.build_context(ranked_chunks, token_budget=token_budget)
        context_ms = (time.perf_counter() - context_start) * 1000

        # ── 7. Prompt Construction ───────────────────────────────────────
        system_prompt, user_prompt = self._prompt_builder.build_prompt(
            parsed_query, context_window, history
        )

        # ── 8. LLM Generation ───────────────────────────────────────────
        llm_start = time.perf_counter()
        llm_response = await self._llm.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
        )
        llm_ms = (time.perf_counter() - llm_start) * 1000

        logger.info(
            "rag_llm_complete",
            model=llm_response.model_name,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            llm_ms=round(llm_ms, 1),
        )

        # ── 9. Response Validation ───────────────────────────────────────
        validation = self._validator.validate(llm_response.content, ranked_chunks)

        # If rejected, return a safe low-confidence response
        answer = llm_response.content
        if not validation.is_valid:
            logger.warning(
                "rag_response_rejected",
                reason=validation.rejection_reason,
                confidence=round(validation.confidence, 3),
            )
            answer = (
                "I was unable to generate a well-grounded answer from the available code context. "
                "This may indicate the repository has not been fully indexed, or the question "
                "requires information not present in the retrieved chunks.\n\n"
                f"_Confidence: {validation.confidence:.1%} (below threshold of "
                f"{settings.MIN_CONFIDENCE_THRESHOLD:.1%})_"
            )

        # ── 10. Citation Generation ──────────────────────────────────────
        citations = self._citation_gen.generate(llm_response.content, ranked_chunks)

        # ── 11. Conversation update ──────────────────────────────────────
        self._conversation.add_user_turn(history, question)
        self._conversation.add_assistant_turn(
            history,
            answer,
            metadata={"intent": parsed_query.intent.value, "confidence": validation.confidence},
        )

        # ── 12. Finalise response ────────────────────────────────────────
        total_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "rag_pipeline_complete",
            session_id=actual_session_id,
            total_ms=round(total_ms, 1),
            retrieval_ms=round(retrieval_ms, 1),
            llm_ms=round(llm_ms, 1),
            confidence=round(validation.confidence, 3),
            num_citations=len(citations),
            intent=parsed_query.intent.value,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            num_retrieved_docs=len(ranked_chunks),
        )

        response = RAGResponse(
            answer=answer,
            citations=citations,
            confidence=validation.confidence,
            intent=parsed_query.intent,
            session_id=actual_session_id,
            repo_id=repo_id,
            latency_ms=total_ms,
            token_usage=TokenUsage(
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens,
                total_tokens=llm_response.total_tokens,
            ),
            retrieved_chunk_count=len(ranked_chunks),
            is_cached=False,
            validation=validation,
            metadata={
                "model": llm_response.model_name,
                "intent": parsed_query.intent.value,
                "rewritten_queries_count": len(parsed_query.rewritten_queries),
                "context_truncated": context_window.truncated,
                "context_tokens": context_window.total_tokens,
                "retrieval_ms": round(retrieval_ms, 1),
                "rerank_ms": round(rerank_ms, 1),
                "context_ms": round(context_ms, 1),
                "llm_ms": round(llm_ms, 1),
            },
        )

        # ── 13. Cache successful response ────────────────────────────────
        if validation.is_valid:
            try:
                await asyncio.to_thread(
                    self._redis.setex,
                    cache_key,
                    settings.RAG_RESPONSE_CACHE_TTL,
                    self._serialise_response(response),
                )
            except Exception as exc:
                logger.debug("rag_cache_write_failed: %s", exc)

        return response

    # ------------------------------------------------------------------
    # Serialisation helpers for Redis caching
    # ------------------------------------------------------------------

    def _serialise_response(self, response: RAGResponse) -> str:
        """Serialise RAGResponse to JSON for Redis storage."""
        data = {
            "answer": response.answer,
            "confidence": response.confidence,
            "intent": response.intent.value,
            "repo_id": response.repo_id,
            "latency_ms": response.latency_ms,
            "retrieved_chunk_count": response.retrieved_chunk_count,
            "is_cached": True,
            "token_usage": {
                "prompt_tokens": response.token_usage.prompt_tokens,
                "completion_tokens": response.token_usage.completion_tokens,
                "total_tokens": response.token_usage.total_tokens,
            },
            "citations": [
                {
                    "file_path": c.file_path,
                    "repo_path": c.repo_path,
                    "class_name": c.class_name,
                    "function_name": c.function_name,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "symbol_type": c.symbol_type,
                    "confidence": c.confidence,
                    "chunk_id": c.chunk_id,
                }
                for c in response.citations
            ],
            "metadata": response.metadata,
        }
        return json.dumps(data)

    def _deserialise_response(self, data: dict, session_id: str) -> RAGResponse:
        """Reconstruct a RAGResponse from cached JSON."""
        from src.domain.models.rag import Citation, QueryIntent, TokenUsage
        return RAGResponse(
            answer=data["answer"],
            citations=[
                Citation(
                    file_path=c["file_path"],
                    repo_path=c["repo_path"],
                    class_name=c.get("class_name"),
                    function_name=c.get("function_name"),
                    start_line=c.get("start_line"),
                    end_line=c.get("end_line"),
                    symbol_type=c.get("symbol_type"),
                    confidence=c["confidence"],
                    chunk_id=c["chunk_id"],
                )
                for c in data.get("citations", [])
            ],
            confidence=data["confidence"],
            intent=QueryIntent(data["intent"]),
            session_id=session_id,
            repo_id=data["repo_id"],
            latency_ms=data["latency_ms"],
            token_usage=TokenUsage(
                prompt_tokens=data["token_usage"]["prompt_tokens"],
                completion_tokens=data["token_usage"]["completion_tokens"],
                total_tokens=data["token_usage"]["total_tokens"],
            ),
            retrieved_chunk_count=data["retrieved_chunk_count"],
            is_cached=True,
            metadata=data.get("metadata", {}),
        )
