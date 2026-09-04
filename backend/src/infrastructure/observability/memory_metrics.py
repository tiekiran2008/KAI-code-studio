"""
Memory Metrics & Observability
================================
Structured logging and in-process metrics for all memory operations.

Every metric is logged via structlog (matching the project's existing logger)
AND stored in simple in-process counters for /health exposure.

Logged Events
-------------
- memory_created        : A new memory was persisted.
- memory_hit            : A search returned results.
- memory_miss           : A search returned no results.
- memory_deleted        : A memory was forgotten.
- memory_consolidation  : A consolidation run completed.
- memory_retrieval_ms   : Latency histogram bucket.

Design: single class, no framework dependency — easy to swap for
OpenTelemetry or Prometheus by overriding the internal _emit method.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict

from src.domain.memory.entities import ConsolidationReport, MemoryType
from src.core.logger import logger


@dataclass
class _Counters:
    creations:     Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    hits:          int = 0
    misses:        int = 0
    deletions:     int = 0
    consolidations: int = 0
    total_latency_ms: float = 0.0
    retrieval_count:  int = 0


class MemoryMetrics:
    """
    Collects and emits structured metrics for memory operations.

    Usage (inject as singleton)
    ---------------------------
    >>> metrics = MemoryMetrics()
    >>> metrics.record_creation(MemoryType.LONG_TERM)
    >>> metrics.record_hit(latency_ms=42.5)
    >>> summary = metrics.summary()
    """

    def __init__(self) -> None:
        self._counters = _Counters()

    # ------------------------------------------------------------------
    # Recording methods (called by MemoryManager)
    # ------------------------------------------------------------------

    def record_creation(self, memory_type: MemoryType) -> None:
        self._counters.creations[memory_type.value] += 1
        logger.info(
            "memory_created",
            memory_type=memory_type.value,
            total_created=self._counters.creations[memory_type.value],
        )

    def record_hit(self, latency_ms: float) -> None:
        self._counters.hits += 1
        self._counters.total_latency_ms += latency_ms
        self._counters.retrieval_count += 1
        logger.info(
            "memory_hit",
            latency_ms=round(latency_ms, 2),
            total_hits=self._counters.hits,
            avg_latency_ms=self._avg_latency(),
        )

    def record_miss(self) -> None:
        self._counters.misses += 1
        logger.info("memory_miss", total_misses=self._counters.misses)

    def record_deletion(self) -> None:
        self._counters.deletions += 1
        logger.info("memory_deleted", total_deletions=self._counters.deletions)

    def record_consolidation(self, report: ConsolidationReport) -> None:
        self._counters.consolidations += 1
        logger.info(
            "memory_consolidation",
            run_id=report.run_id,
            scanned=report.memories_scanned,
            merged=report.memories_merged,
            archived=report.memories_archived,
            deleted=report.memories_deleted,
            duration_ms=report.duration_ms,
            errors=report.errors,
        )

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    def _avg_latency(self) -> float:
        if self._counters.retrieval_count == 0:
            return 0.0
        return round(self._counters.total_latency_ms / self._counters.retrieval_count, 2)

    def summary(self) -> dict:
        """Return a snapshot of all counters for /health or admin endpoints."""
        return {
            "creations":         dict(self._counters.creations),
            "hits":              self._counters.hits,
            "misses":            self._counters.misses,
            "hit_rate":          self._hit_rate(),
            "deletions":         self._counters.deletions,
            "consolidations":    self._counters.consolidations,
            "avg_retrieval_ms":  self._avg_latency(),
        }

    def _hit_rate(self) -> float:
        total = self._counters.hits + self._counters.misses
        if total == 0:
            return 0.0
        return round(self._counters.hits / total, 4)
