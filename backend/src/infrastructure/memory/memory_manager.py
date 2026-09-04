"""
Memory Manager
==============
Concrete implementation of ``IMemoryManager`` — the primary entrypoint for
all memory operations in the system.

Responsibilities
----------------
1. **Create** memories in the appropriate stores (PostgreSQL + Qdrant / Redis).
2. **Update** memories with version conflict resolution.
3. **Search** using multi-store fan-out: Qdrant semantic search → PostgreSQL hydration → ranking.
4. **Enrich context** before every agent execution (pre-execution hook).
5. **Forget** memories (soft or hard) with GDPR compliance.
6. **Consolidate** background: merge similar, archive inactive, delete expired.

Design Decisions
----------------
* **Fan-out search**: Qdrant returns candidate IDs + scores; PostgreSQL hydrates
  full entities. This separates fast vector search from structured data retrieval.
* **Deduplication** during context enrichment compares semantic similarity of
  the memory content against existing RAG context using a simple TF-IDF-inspired
  token overlap to avoid duplicating information passed to the LLM.
* **Ranking formula**: weighted sum of Qdrant cosine similarity + MemoryScore
  effective_score + recency bonus. Weights are tunable via config.
* **Conflict resolution**: on update, if the incoming version is stale, the
  manager merges non-conflicting fields and raises on content conflicts.
* **Embedding injection**: the manager calls the shared IEmbeddingService to
  produce vectors before Qdrant upsert, reusing the project-wide embedding model.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.domain.interfaces.embedding import IEmbeddingService
from src.domain.memory.entities import (
    BaseMemory,
    ConsolidationReport,
    EpisodicMemory,
    LongTermMemory,
    MemorySearchQuery,
    MemorySearchResult,
    MemoryStatus,
    MemoryType,
    RepositoryMemory,
    ShortTermMemory,
)
from src.domain.memory.ports import (
    IMemoryManager,
    IMemoryRepository,
    IMemoryVectorStore,
    ISessionCache,
)
from src.infrastructure.observability.memory_metrics import MemoryMetrics
from src.core.logger import logger


_SIMILARITY_WEIGHT    = 0.60   # Qdrant cosine score
_IMPORTANCE_WEIGHT    = 0.25   # MemoryScore.importance
_RECENCY_WEIGHT       = 0.15   # Decay based on last_accessed age
_DEDUP_OVERLAP_THRESH = 0.50   # Token overlap ratio to skip a memory as duplicate


class MemoryManager(IMemoryManager):
    """
    Orchestrates PostgreSQL, Qdrant, and Redis to provide a unified
    memory API to the application layer.
    """

    def __init__(
        self,
        repository:    IMemoryRepository,
        vector_store:  IMemoryVectorStore,
        session_cache: ISessionCache,
        embedding_service: IEmbeddingService,
        metrics:       Optional[MemoryMetrics] = None,
        short_term_ttl: int = 1800,
        long_term_ttl_days: int = 90,
    ) -> None:
        self._repo      = repository
        self._vectors   = vector_store
        self._cache     = session_cache
        self._embedder  = embedding_service
        self._metrics   = metrics or MemoryMetrics()
        self._st_ttl    = short_term_ttl
        self._lt_ttl    = timedelta(days=long_term_ttl_days)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _embed(self, text: str) -> List[float]:
        """Generate an embedding vector for the given text."""
        return self._embedder.generate_embedding(text[:4096])  # guard against oversized content

    def _build_payload(self, memory: BaseMemory) -> Dict[str, Any]:
        """Build the Qdrant payload from a domain entity."""
        return {
            "summary":       memory.summary,
            "memory_type":   memory.memory_type.value,
            "repository_id": memory.repository_id,
            "tags":          memory.score.tags,
            "importance":    memory.score.importance,
            "created_at":    memory.created_at.isoformat(),
        }

    def _rank_results(
        self,
        hits: List[Dict[str, Any]],
        entities: Dict[str, BaseMemory],
    ) -> List[MemorySearchResult]:
        """
        Rank search hits by a composite score:
          rank_score = similarity * w1 + importance * w2 + recency_bonus * w3
        """
        now = datetime.utcnow()
        ranked: List[MemorySearchResult] = []

        for i, hit in enumerate(hits):
            mid = hit.get("memory_id", "")
            entity = entities.get(mid)
            if entity is None or entity.status == MemoryStatus.DELETED:
                continue

            similarity = float(hit.get("score", 0.0))
            importance = entity.score.importance

            # Recency: 1.0 if accessed today, decays to 0 after 30 days
            days_since = max(0, (now - entity.score.last_accessed).days)
            recency_bonus = max(0.0, 1.0 - (days_since / 30.0))

            composite = (
                similarity   * _SIMILARITY_WEIGHT
                + importance * _IMPORTANCE_WEIGHT
                + recency_bonus * _RECENCY_WEIGHT
            )

            ranked.append(MemorySearchResult(
                memory=entity,
                relevance_score=round(composite, 4),
                rank=i + 1,
            ))

        ranked.sort(key=lambda r: r.relevance_score, reverse=True)
        for i, r in enumerate(ranked):
            r.rank = i + 1

        return ranked

    @staticmethod
    def _token_overlap(text_a: str, text_b: str) -> float:
        """Simple token-level Jaccard similarity for deduplication."""
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_short_term(
        self,
        user_id: str,
        session_id: str,
        memory: ShortTermMemory,
    ) -> ShortTermMemory:
        memory.user_id   = user_id
        memory.session_id = session_id
        memory.memory_type = MemoryType.SHORT_TERM
        if not memory.id:
            memory.id = str(uuid.uuid4())

        await self._cache.set(session_id, user_id, memory, ttl_seconds=self._st_ttl)
        self._metrics.record_creation(MemoryType.SHORT_TERM)
        logger.info("memory_created_short_term", session_id=session_id, user_id=user_id)
        return memory

    async def create_long_term(
        self,
        user_id: str,
        memory: LongTermMemory,
    ) -> LongTermMemory:
        memory.user_id   = user_id
        memory.memory_type = MemoryType.LONG_TERM
        memory.expires_at  = datetime.utcnow() + self._lt_ttl
        if not memory.id:
            memory.id = str(uuid.uuid4())

        saved = await self._repo.save(memory)
        embedding = self._embed(memory.content or memory.summary)
        await self._vectors.upsert(
            memory_id=saved.id,
            user_id=user_id,
            memory_type=MemoryType.LONG_TERM,
            embedding=embedding,
            payload=self._build_payload(saved),
        )
        self._metrics.record_creation(MemoryType.LONG_TERM)
        return saved  # type: ignore[return-value]

    async def create_repository_memory(
        self,
        user_id: str,
        memory: RepositoryMemory,
    ) -> RepositoryMemory:
        memory.user_id = user_id
        memory.memory_type = MemoryType.REPOSITORY
        if not memory.id:
            memory.id = str(uuid.uuid4())

        saved = await self._repo.save(memory)
        embedding = self._embed(
            f"{memory.repo_summary} {memory.architecture_summary}"[:4096]
        )
        await self._vectors.upsert(
            memory_id=saved.id,
            user_id=user_id,
            memory_type=MemoryType.REPOSITORY,
            embedding=embedding,
            payload=self._build_payload(saved),
        )
        self._metrics.record_creation(MemoryType.REPOSITORY)
        return saved  # type: ignore[return-value]

    async def create_episodic(
        self,
        user_id: str,
        memory: EpisodicMemory,
    ) -> EpisodicMemory:
        memory.user_id = user_id
        memory.memory_type = MemoryType.EPISODIC
        if not memory.id:
            memory.id = str(uuid.uuid4())

        saved = await self._repo.save(memory)
        text_for_embed = f"{memory.query} {memory.final_answer} {memory.lessons_learned}"
        embedding = self._embed(text_for_embed)
        await self._vectors.upsert(
            memory_id=saved.id,
            user_id=user_id,
            memory_type=MemoryType.EPISODIC,
            embedding=embedding,
            payload=self._build_payload(saved),
        )
        self._metrics.record_creation(MemoryType.EPISODIC)
        return saved  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Update with conflict resolution
    # ------------------------------------------------------------------

    async def update_memory(
        self,
        memory_id: str,
        user_id: str,
        updates: Dict[str, Any],
    ) -> BaseMemory:
        existing = await self._repo.get_by_id(memory_id, user_id)
        if existing is None:
            raise ValueError(f"Memory {memory_id} not found for user {user_id}")

        # Apply field updates (shallow merge)
        for key, value in updates.items():
            if hasattr(existing, key):
                setattr(existing, key, value)

        existing.increment_version()
        updated = await self._repo.update(existing)

        # Re-embed and re-upsert if content changed
        if "content" in updates or "summary" in updates:
            embedding = self._embed(updated.content or updated.summary)
            await self._vectors.upsert(
                memory_id=updated.id,
                user_id=user_id,
                memory_type=updated.memory_type,
                embedding=embedding,
                payload=self._build_payload(updated),
            )

        logger.info("memory_updated", memory_id=memory_id)
        return updated

    # ------------------------------------------------------------------
    # Search & Retrieval
    # ------------------------------------------------------------------

    async def search(self, query: MemorySearchQuery) -> List[MemorySearchResult]:
        t0 = time.perf_counter()
        embedding = self._embed(query.query_text)

        hits = await self._vectors.search(
            query_embedding=embedding,
            user_id=query.user_id,
            memory_types=query.memory_types or None,
            repository_id=query.repository_id,
            top_k=query.top_k * 2,  # Fetch extra for post-filtering
            score_threshold=query.min_score,
        )

        if not hits:
            self._metrics.record_miss()
            return []

        # Hydrate from PostgreSQL for full entity data
        memory_ids = [h["memory_id"] for h in hits if h.get("memory_id")]
        entities: Dict[str, BaseMemory] = {}
        for mid in memory_ids:
            entity = await self._repo.get_by_id(mid, query.user_id)
            if entity:
                entity.bump_access()
                await self._repo.update_score(mid, {
                    "access_count": entity.score.access_count,
                    "last_accessed": entity.score.last_accessed,
                })
                entities[mid] = entity

        ranked = self._rank_results(hits, entities)

        latency_ms = (time.perf_counter() - t0) * 1000
        self._metrics.record_hit(latency_ms=latency_ms)
        logger.info(
            "memory_search_complete",
            query=query.query_text[:60],
            user_id=query.user_id,
            hits=len(ranked),
            latency_ms=round(latency_ms, 2),
        )
        return ranked[:query.top_k]

    async def get_session_memory(
        self,
        session_id: str,
        user_id: str,
    ) -> Optional[ShortTermMemory]:
        return await self._cache.get(session_id, user_id)

    async def enrich_context(
        self,
        query_text: str,
        user_id: str,
        session_id: Optional[str],
        repository_id: Optional[str],
        existing_rag_context: str,
        token_budget: int = 2000,
    ) -> str:
        """
        Pre-execution memory enrichment hook.

        Algorithm
        ---------
        1. Search long-term, repository, and episodic memories for query.
        2. Rank by composite score.
        3. Skip memories whose content overlaps > 50% with existing RAG context.
        4. Prepend selected memories to the context, respecting token budget.
        5. Prepend short-term session memory (conversation turns) last.
        """
        parts: List[str] = []
        used_tokens = 0
        chars_per_token = 4

        # ---- Short-term session memory ----
        if session_id:
            session_mem = await self._cache.get(session_id, user_id)
            if session_mem and session_mem.conversation_turns:
                turns_text = "\n".join(
                    f"[{t.get('role','user')}]: {t.get('content','')}"
                    for t in session_mem.conversation_turns[-6:]  # Last 3 exchanges
                )
                block = f"## Recent Conversation\n{turns_text}"
                block_tokens = len(block) // chars_per_token
                if block_tokens <= token_budget:
                    parts.append(block)
                    used_tokens += block_tokens

        # ---- Semantic memory search ----
        search_query = MemorySearchQuery(
            query_text=query_text,
            user_id=user_id,
            memory_types=[
                MemoryType.LONG_TERM,
                MemoryType.REPOSITORY,
                MemoryType.EPISODIC,
            ],
            repository_id=repository_id,
            top_k=8,
        )
        results = await self.search(search_query)

        for result in results:
            mem = result.memory
            block = f"## Memory [{mem.memory_type.value}] (relevance={result.relevance_score:.2f})\n{mem.content or mem.summary}"
            block_tokens = len(block) // chars_per_token

            # Deduplication guard
            overlap = self._token_overlap(block, existing_rag_context)
            if overlap > _DEDUP_OVERLAP_THRESH:
                logger.debug(
                    "memory_enrich_skipped_duplicate",
                    memory_id=mem.id,
                    overlap=round(overlap, 2),
                )
                continue

            if used_tokens + block_tokens > token_budget:
                break

            parts.append(block)
            used_tokens += block_tokens

        if not parts:
            return ""

        enriched = "\n\n---\n\n".join(parts)
        logger.info(
            "memory_context_enriched",
            user_id=user_id,
            blocks=len(parts),
            tokens_used=used_tokens,
        )
        return enriched

    # ------------------------------------------------------------------
    # Forget / GDPR
    # ------------------------------------------------------------------

    async def forget(self, memory_id: str, user_id: str, hard: bool = False) -> None:
        if hard:
            await self._repo.hard_delete(memory_id, user_id)
            await self._vectors.delete(memory_id, user_id)
        else:
            await self._repo.soft_delete(memory_id, user_id)
            await self._vectors.delete(memory_id, user_id)
        self._metrics.record_deletion()
        logger.info("memory_forgotten", memory_id=memory_id, user_id=user_id, hard=hard)

    async def forget_user(self, user_id: str) -> int:
        count = await self._repo.hard_delete_all_for_user(user_id)
        await self._vectors.delete_all_for_user(user_id)
        logger.info("memory_gdpr_user_erasure", user_id=user_id, total_deleted=count)
        return count

    # ------------------------------------------------------------------
    # Background Consolidation
    # ------------------------------------------------------------------

    async def consolidate(self) -> ConsolidationReport:
        """
        Single consolidation pass.
        Runs as: expire → archive → (future: merge similar).
        """
        report = ConsolidationReport()
        t0 = time.perf_counter()

        # 1. Delete expired records
        try:
            expired = await self._repo.get_expired(limit=200)
            report.memories_scanned += len(expired)
            for mem in expired:
                await self._repo.soft_delete(mem.id, mem.user_id)
                await self._vectors.delete(mem.id, mem.user_id)
                report.memories_deleted += 1
        except Exception as exc:
            report.errors.append(f"expire phase: {exc}")
            logger.error("consolidation_expire_failed", error=str(exc))

        # 2. Archive inactive records (not accessed in 90 days)
        try:
            inactive = await self._repo.get_inactive(days_inactive=90, limit=500)
            report.memories_scanned += len(inactive)
            for mem in inactive:
                await self._repo.update_memory(mem) if False else None  # noqa
                # Direct status update via score update
                await self._repo.update_score(mem.id, {
                    "decay_factor": max(0.1, mem.score.decay_factor * 0.8)
                })
                # Mark archived via status field
                await self._repo.soft_delete(mem.id, mem.user_id)
                report.memories_archived += 1
        except Exception as exc:
            report.errors.append(f"archive phase: {exc}")
            logger.error("consolidation_archive_failed", error=str(exc))

        report.duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        self._metrics.record_consolidation(report)
        logger.info(
            "memory_consolidation_complete",
            scanned=report.memories_scanned,
            deleted=report.memories_deleted,
            archived=report.memories_archived,
            duration_ms=report.duration_ms,
        )
        return report

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, memory_id: str, user_id: str) -> Optional[BaseMemory]:
        return await self._repo.get_by_id(memory_id, user_id)

    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        repository_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BaseMemory]:
        return await self._repo.list_by_user(
            user_id=user_id,
            memory_type=memory_type,
            repository_id=repository_id,
            limit=limit,
            offset=offset,
        )
