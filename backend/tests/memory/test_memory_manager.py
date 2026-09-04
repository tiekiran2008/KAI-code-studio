"""
Unit Tests — Memory Manager
===========================
Tests the orchestrator logic (fan-out search, deduplication, conflict handling)
using mocked dependencies.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.infrastructure.memory.memory_manager import MemoryManager
from src.domain.memory.entities import (
    MemoryScore,
    MemoryType,
    ShortTermMemory,
    LongTermMemory,
    MemorySearchQuery,
    MemorySearchResult,
)
from src.infrastructure.observability.memory_metrics import MemoryMetrics


@pytest.fixture
def mock_repo():
    return AsyncMock()

@pytest.fixture
def mock_vectors():
    return AsyncMock()

@pytest.fixture
def mock_cache():
    return AsyncMock()

@pytest.fixture
def mock_embedder():
    embedder = MagicMock()
    embedder.generate_embedding.return_value = [0.1] * 384
    return embedder

@pytest.fixture
def manager(mock_repo, mock_vectors, mock_cache, mock_embedder):
    return MemoryManager(
        repository=mock_repo,
        vector_store=mock_vectors,
        session_cache=mock_cache,
        embedding_service=mock_embedder,
        metrics=MemoryMetrics(),
    )


@pytest.mark.asyncio
async def test_create_short_term(manager, mock_cache):
    mem = ShortTermMemory(content="task context")
    result = await manager.create_short_term("user1", "sess1", mem)
    
    assert result.user_id == "user1"
    assert result.session_id == "sess1"
    assert result.memory_type == MemoryType.SHORT_TERM
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_create_long_term_upserts_both_stores(manager, mock_repo, mock_vectors, mock_embedder):
    mem = LongTermMemory(content="likes python")
    mock_repo.save.return_value = mem
    
    await manager.create_long_term("user1", mem)
    
    mock_repo.save.assert_called_once()
    mock_embedder.generate_embedding.assert_called_once_with("likes python")
    mock_vectors.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_search_fan_out_and_rank(manager, mock_vectors, mock_repo):
    # Vector store returns hits
    mock_vectors.search.return_value = [
        {"memory_id": "mem1", "score": 0.9},
        {"memory_id": "mem2", "score": 0.8},
    ]
    
    # DB hydrates entities
    mem1 = LongTermMemory(id="mem1", user_id="user1", score=MemoryScore(importance=0.9))
    mem2 = LongTermMemory(id="mem2", user_id="user1", score=MemoryScore(importance=0.5))
    
    async def mock_get_by_id(mid, uid):
        return mem1 if mid == "mem1" else mem2
    mock_repo.get_by_id.side_effect = mock_get_by_id
    
    query = MemorySearchQuery(query_text="python", user_id="user1", top_k=2)
    results = await manager.search(query)
    
    assert len(results) == 2
    assert results[0].memory.id == "mem1"  # mem1 has higher importance and similarity
    assert results[1].memory.id == "mem2"


def test_token_overlap():
    text_a = "def fibonacci(n): return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)"
    text_b = "def fibonacci(n): return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)"
    assert MemoryManager._token_overlap(text_a, text_b) == 1.0
    
    text_c = "class AuthHandler: pass"
    assert MemoryManager._token_overlap(text_a, text_c) == 0.0


@pytest.mark.asyncio
async def test_enrich_context_deduplication(manager, mock_vectors, mock_repo, mock_cache):
    # Mock short term memory
    mock_cache.get.return_value = None
    
    # Mock search results
    mock_vectors.search.return_value = [{"memory_id": "mem1", "score": 0.9}]
    mem1 = LongTermMemory(id="mem1", user_id="u1", content="existing rag block exact match")
    mock_repo.get_by_id.return_value = mem1
    
    enriched = await manager.enrich_context(
        query_text="test",
        user_id="u1",
        session_id=None,
        repository_id=None,
        existing_rag_context="existing rag block exact match",
        token_budget=1000
    )
    
    # Should be skipped due to overlap > 0.50
    assert enriched == ""


@pytest.mark.asyncio
async def test_consolidate_expires_and_archives(manager, mock_repo, mock_vectors):
    mem_exp = ShortTermMemory(id="exp1", user_id="u1")
    mem_arc = LongTermMemory(id="arc1", user_id="u1", score=MemoryScore())
    
    mock_repo.get_expired.return_value = [mem_exp]
    mock_repo.get_inactive.return_value = [mem_arc]
    
    report = await manager.consolidate()
    
    assert report.memories_scanned == 2
    assert report.memories_deleted == 1
    assert report.memories_archived == 1
    
    # Verify deletions
    mock_repo.soft_delete.assert_any_call("exp1", "u1")
    mock_vectors.delete.assert_any_call("exp1", "u1")
    
    # Verify archiving (via score and soft delete)
    mock_repo.update_score.assert_called_with("arc1", {"decay_factor": 0.8})
    mock_repo.soft_delete.assert_any_call("arc1", "u1")
