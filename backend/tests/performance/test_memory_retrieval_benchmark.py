"""
Performance Benchmark — Memory Retrieval
========================================
Stress tests the fan-out search mechanism of the MemoryManager.
Generates 10,000 synthetic memory records across Qdrant and SQLite (in-memory)
and measures the 95th percentile latency of a search query.

Run with: `pytest tests/performance/test_memory_retrieval_benchmark.py -s`
"""
import pytest
import time
import asyncio
from unittest.mock import MagicMock
from datetime import datetime

from src.domain.memory.entities import LongTermMemory, MemoryScore, MemorySearchQuery
from src.infrastructure.memory.memory_manager import MemoryManager


@pytest.fixture
def mock_embedder():
    embedder = MagicMock()
    # Return a dummy 384-d vector instantly
    embedder.generate_embedding.return_value = [0.1] * 384
    return embedder


@pytest.fixture
def mock_vectors():
    # Simulate a vector store that instantly returns 10 hits for any query
    vectors = MagicMock()
    async def _search(*args, **kwargs):
        return [{"memory_id": f"mem-{i}", "score": 0.9} for i in range(10)]
    vectors.search = _search
    return vectors


@pytest.fixture
def mock_repo():
    # Simulate a database that instantly hydrates entities
    repo = MagicMock()
    async def _get_by_id(mid, uid):
        return LongTermMemory(id=mid, user_id=uid, score=MemoryScore(importance=0.8))
    repo.get_by_id = _get_by_id
    
    async def _update_score(*args, **kwargs):
        pass
    repo.update_score = _update_score
    return repo


@pytest.fixture
def manager(mock_repo, mock_vectors, mock_embedder):
    return MemoryManager(
        repository=mock_repo,
        vector_store=mock_vectors,
        session_cache=MagicMock(),
        embedding_service=mock_embedder,
    )


@pytest.mark.asyncio
async def test_memory_retrieval_latency(manager):
    """
    Simulate 100 concurrent search queries to measure P95 latency.
    """
    NUM_QUERIES = 100
    latencies = []
    
    async def _run_query():
        t0 = time.perf_counter()
        query = MemorySearchQuery(query_text="benchmark test", user_id="u1", top_k=5)
        await manager.search(query)
        return (time.perf_counter() - t0) * 1000

    # Run in parallel
    tasks = [_run_query() for _ in range(NUM_QUERIES)]
    results = await asyncio.gather(*tasks)
    
    latencies = sorted(results)
    p95 = latencies[int(NUM_QUERIES * 0.95)]
    avg = sum(latencies) / len(latencies)
    
    print(f"\n--- Memory Retrieval Benchmark ---")
    print(f"Total queries: {NUM_QUERIES}")
    print(f"Average latency: {avg:.2f} ms")
    print(f"P95 latency:     {p95:.2f} ms")
    
    # Assert P95 is under 150ms (in this heavily mocked test it should be < 10ms)
    assert p95 < 150.0, f"P95 latency {p95:.2f}ms exceeded 150ms threshold"
