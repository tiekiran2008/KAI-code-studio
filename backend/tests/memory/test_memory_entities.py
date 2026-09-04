"""
Unit Tests — Memory Domain Entities
=====================================
Tests every domain entity, MemoryScore, and the lifecycle helpers.
No external dependencies required.
"""
import pytest
from datetime import datetime, timedelta

from src.domain.memory.entities import (
    EpisodicMemory,
    EpisodeType,
    LongTermMemory,
    MemoryScore,
    MemorySearchQuery,
    MemoryStatus,
    MemoryType,
    RepositoryMemory,
    ShortTermMemory,
    UserPreferences,
    PreferredExplanationDepth,
    ConsolidationReport,
)


# ---------------------------------------------------------------------------
# MemoryScore
# ---------------------------------------------------------------------------

class TestMemoryScore:
    def test_default_values(self):
        score = MemoryScore()
        assert score.importance == 0.5
        assert score.confidence == 0.8
        assert score.access_count == 0
        assert score.decay_factor == 1.0
        assert score.tags == []

    def test_effective_score_increases_with_access(self):
        score = MemoryScore(importance=0.8, confidence=0.9, decay_factor=1.0)
        score.access_count = 0
        base = score.effective_score()
        score.access_count = 10
        assert score.effective_score() > base

    def test_effective_score_clamped_to_1(self):
        score = MemoryScore(importance=1.0, confidence=1.0, decay_factor=1.0, access_count=9999)
        assert score.effective_score() <= 1.0

    def test_effective_score_zero_with_zero_importance(self):
        score = MemoryScore(importance=0.0, confidence=1.0)
        assert score.effective_score() == 0.0


# ---------------------------------------------------------------------------
# ShortTermMemory
# ---------------------------------------------------------------------------

class TestShortTermMemory:
    def test_default_type(self):
        mem = ShortTermMemory()
        assert mem.memory_type == MemoryType.SHORT_TERM

    def test_is_expired_no_ttl(self):
        mem = ShortTermMemory()
        assert mem.is_expired() is False

    def test_is_expired_past_ttl(self):
        mem = ShortTermMemory(expires_at=datetime.utcnow() - timedelta(seconds=1))
        assert mem.is_expired() is True

    def test_is_not_expired_future_ttl(self):
        mem = ShortTermMemory(expires_at=datetime.utcnow() + timedelta(hours=1))
        assert mem.is_expired() is False

    def test_bump_access_increments_count(self):
        mem = ShortTermMemory()
        mem.bump_access()
        assert mem.score.access_count == 1
        mem.bump_access()
        assert mem.score.access_count == 2

    def test_increment_version(self):
        mem = ShortTermMemory(version=1)
        mem.increment_version()
        assert mem.version == 2


# ---------------------------------------------------------------------------
# LongTermMemory
# ---------------------------------------------------------------------------

class TestLongTermMemory:
    def test_default_preferences(self):
        mem = LongTermMemory()
        assert mem.preferences.preferred_languages == []
        assert mem.preferences.explanation_depth == PreferredExplanationDepth.STANDARD

    def test_set_preferences(self):
        prefs = UserPreferences(
            preferred_languages=["python", "typescript"],
            explanation_depth=PreferredExplanationDepth.DETAILED,
        )
        mem = LongTermMemory(preferences=prefs)
        assert "python" in mem.preferences.preferred_languages
        assert mem.preferences.explanation_depth == PreferredExplanationDepth.DETAILED


# ---------------------------------------------------------------------------
# RepositoryMemory
# ---------------------------------------------------------------------------

class TestRepositoryMemory:
    def test_default_type(self):
        mem = RepositoryMemory()
        assert mem.memory_type == MemoryType.REPOSITORY

    def test_tech_stack_stored(self):
        mem = RepositoryMemory(tech_stack=["python", "fastapi", "postgresql"])
        assert "fastapi" in mem.tech_stack


# ---------------------------------------------------------------------------
# EpisodicMemory
# ---------------------------------------------------------------------------

class TestEpisodicMemory:
    def test_default_episode_type(self):
        mem = EpisodicMemory()
        assert mem.episode_type == EpisodeType.GENERAL

    def test_confidence_stored(self):
        mem = EpisodicMemory(confidence_score=0.92)
        assert mem.confidence_score == pytest.approx(0.92)


# ---------------------------------------------------------------------------
# MemorySearchQuery
# ---------------------------------------------------------------------------

class TestMemorySearchQuery:
    def test_defaults(self):
        q = MemorySearchQuery(query_text="test query", user_id="user-1")
        assert q.top_k == 5
        assert q.min_score == 0.0
        assert q.include_archived is False

    def test_custom_memory_types(self):
        q = MemorySearchQuery(
            query_text="debug session",
            user_id="user-1",
            memory_types=[MemoryType.EPISODIC],
        )
        assert MemoryType.EPISODIC in q.memory_types


# ---------------------------------------------------------------------------
# ConsolidationReport
# ---------------------------------------------------------------------------

class TestConsolidationReport:
    def test_default_zeros(self):
        report = ConsolidationReport()
        assert report.memories_scanned == 0
        assert report.memories_merged == 0
        assert report.memories_archived == 0
        assert report.memories_deleted == 0
        assert report.errors == []

    def test_run_id_is_uuid(self):
        import uuid
        report = ConsolidationReport()
        uuid.UUID(report.run_id)  # Must not raise


# ---------------------------------------------------------------------------
# MemoryStatus lifecycle
# ---------------------------------------------------------------------------

class TestMemoryStatus:
    def test_soft_delete_state(self):
        mem = ShortTermMemory(status=MemoryStatus.DELETED)
        assert mem.status == MemoryStatus.DELETED

    def test_archive_state(self):
        mem = LongTermMemory(status=MemoryStatus.ARCHIVED)
        assert mem.status == MemoryStatus.ARCHIVED
