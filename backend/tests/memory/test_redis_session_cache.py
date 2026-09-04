"""
Unit Tests — Redis Session Cache
=================================
Uses a MagicMock Redis client to test serialisation/deserialisation,
TTL handling, and isolation semantics without a real Redis instance.
"""
import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from src.domain.memory.entities import (
    MemoryScore,
    MemoryStatus,
    MemoryType,
    ShortTermMemory,
)
from src.infrastructure.memory.redis_session_cache import (
    RedisSessionCache,
    _serialize,
    _deserialize,
    _make_key,
)


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------

class TestSerialisation:
    def _sample_memory(self) -> ShortTermMemory:
        return ShortTermMemory(
            id="test-id-1",
            user_id="user-123",
            session_id="sess-abc",
            memory_type=MemoryType.SHORT_TERM,
            content="Discuss authentication module",
            summary="Auth session",
            version=1,
            status=MemoryStatus.ACTIVE,
            score=MemoryScore(importance=0.7, tags=["auth", "backend"]),
            conversation_turns=[{"role": "user", "content": "How does auth work?"}],
            current_task="Explain auth module",
        )

    def test_roundtrip(self):
        mem = self._sample_memory()
        serialized = _serialize(mem)
        recovered = _deserialize(serialized)

        assert recovered.id == mem.id
        assert recovered.user_id == mem.user_id
        assert recovered.session_id == mem.session_id
        assert recovered.content == mem.content
        assert recovered.score.importance == pytest.approx(mem.score.importance)
        assert recovered.score.tags == mem.score.tags
        assert len(recovered.conversation_turns) == 1
        assert recovered.current_task == mem.current_task

    def test_serialised_is_valid_json(self):
        mem = self._sample_memory()
        raw = _serialize(mem)
        parsed = json.loads(raw)
        assert parsed["id"] == "test-id-1"
        assert parsed["session_id"] == "sess-abc"

    def test_none_expires_at_serialised_correctly(self):
        mem = self._sample_memory()
        mem.expires_at = None
        raw = _serialize(mem)
        parsed = json.loads(raw)
        assert parsed["expires_at"] is None

    def test_expires_at_roundtrip(self):
        mem = self._sample_memory()
        mem.expires_at = datetime(2026, 12, 31, 23, 59, 59)
        raw = _serialize(mem)
        recovered = _deserialize(raw)
        assert recovered.expires_at.year == 2026


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

class TestKeyGeneration:
    def test_key_format(self):
        key = _make_key("user-123", "sess-abc")
        assert key == "memory:session:user-123:sess-abc"

    def test_different_users_different_keys(self):
        key1 = _make_key("user-A", "sess-1")
        key2 = _make_key("user-B", "sess-1")
        assert key1 != key2


# ---------------------------------------------------------------------------
# RedisSessionCache (mocked Redis)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    return MagicMock()


@pytest.fixture
def cache(mock_redis):
    return RedisSessionCache(mock_redis)


@pytest.fixture
def sample_memory():
    return ShortTermMemory(
        id="mem-001",
        user_id="user-1",
        session_id="sess-1",
        content="test content",
        summary="test summary",
        score=MemoryScore(),
    )


@pytest.mark.asyncio
async def test_set_calls_redis_setex(cache, mock_redis, sample_memory):
    await cache.set("sess-1", "user-1", sample_memory, ttl_seconds=600)
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "memory:session:user-1:sess-1"
    assert call_args[0][1] == 600


@pytest.mark.asyncio
async def test_get_returns_none_when_missing(cache, mock_redis):
    mock_redis.get.return_value = None
    result = await cache.get("sess-missing", "user-1")
    assert result is None


@pytest.mark.asyncio
async def test_get_returns_memory_when_present(cache, mock_redis, sample_memory):
    serialized = _serialize(sample_memory).encode("utf-8")
    mock_redis.get.return_value = serialized
    result = await cache.get("sess-1", "user-1")
    assert result is not None
    assert result.id == sample_memory.id
    assert result.content == sample_memory.content


@pytest.mark.asyncio
async def test_delete_calls_redis_delete(cache, mock_redis):
    await cache.delete("sess-1", "user-1")
    mock_redis.delete.assert_called_once_with("memory:session:user-1:sess-1")


@pytest.mark.asyncio
async def test_extend_ttl_calls_expire(cache, mock_redis):
    await cache.extend_ttl("sess-1", "user-1", 3600)
    mock_redis.expire.assert_called_once_with("memory:session:user-1:sess-1", 3600)


@pytest.mark.asyncio
async def test_exists_true(cache, mock_redis):
    mock_redis.exists.return_value = 1
    assert await cache.exists("sess-1", "user-1") is True


@pytest.mark.asyncio
async def test_exists_false(cache, mock_redis):
    mock_redis.exists.return_value = 0
    assert await cache.exists("sess-1", "user-1") is False
