"""
Redis Session Cache
===================
Implements ``ISessionCache`` using Redis for volatile short-term session memory.

Design Decisions
----------------
* **Key schema**: ``memory:session:{user_id}:{session_id}`` — namespaced to
  prevent collisions with existing RAG session keys and to enable
  key-pattern scanning for user-level operations.
* **Serialisation**: JSON (stdlib) for portability. Datetime fields are
  serialised to ISO-8601 strings and deserialised back on read.
* **Sync redis client** (matching the existing ``dependencies.py`` pattern).
  Blocking calls are wrapped in ``run_in_executor`` for async compat.
* **Per-user isolation** is enforced at the key level — a user can only
  access sessions prefixed with their own ``user_id``.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from functools import partial
from typing import Any, Dict, Optional

import redis

from src.domain.memory.entities import (
    MemoryScore,
    MemoryStatus,
    MemoryType,
    ShortTermMemory,
)
from src.domain.memory.ports import ISessionCache
from src.core.logger import logger


_KEY_PREFIX = "memory:session"
_DEFAULT_TTL = 1800  # 30 minutes


def _make_key(user_id: str, session_id: str) -> str:
    return f"{_KEY_PREFIX}:{user_id}:{session_id}"


def _serialize(memory: ShortTermMemory) -> str:
    """Convert ShortTermMemory to a JSON string with ISO datetime encoding."""
    def _default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "value"):
            return obj.value
        return str(obj)

    return json.dumps(
        {
            "id": memory.id,
            "user_id": memory.user_id,
            "repository_id": memory.repository_id,
            "memory_type": memory.memory_type.value,
            "content": memory.content,
            "summary": memory.summary,
            "version": memory.version,
            "status": memory.status.value,
            "score": {
                "importance": memory.score.importance,
                "confidence": memory.score.confidence,
                "access_count": memory.score.access_count,
                "last_accessed": memory.score.last_accessed.isoformat(),
                "decay_factor": memory.score.decay_factor,
                "source": memory.score.source,
                "tags": memory.score.tags,
            },
            "created_at": memory.created_at.isoformat(),
            "expires_at": memory.expires_at.isoformat() if memory.expires_at else None,
            "metadata": memory.metadata,
            "session_id": memory.session_id,
            "conversation_turns": memory.conversation_turns,
            "active_plan": memory.active_plan,
            "current_task": memory.current_task,
            "recent_document_ids": memory.recent_document_ids,
        },
        default=_default,
    )


def _deserialize(raw: str) -> ShortTermMemory:
    """Reconstruct a ShortTermMemory from a JSON string."""
    data: Dict[str, Any] = json.loads(raw)
    score_data = data.get("score", {})
    score = MemoryScore(
        importance=score_data.get("importance", 0.5),
        confidence=score_data.get("confidence", 0.8),
        access_count=score_data.get("access_count", 0),
        last_accessed=datetime.fromisoformat(
            score_data.get("last_accessed", datetime.utcnow().isoformat())
        ),
        decay_factor=score_data.get("decay_factor", 1.0),
        source=score_data.get("source", "system"),
        tags=score_data.get("tags", []),
    )
    return ShortTermMemory(
        id=data["id"],
        user_id=data["user_id"],
        repository_id=data.get("repository_id"),
        memory_type=MemoryType(data.get("memory_type", "short_term")),
        content=data.get("content", ""),
        summary=data.get("summary", ""),
        version=data.get("version", 1),
        status=MemoryStatus(data.get("status", "active")),
        score=score,
        created_at=datetime.fromisoformat(data["created_at"]),
        expires_at=(
            datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None
        ),
        metadata=data.get("metadata", {}),
        session_id=data.get("session_id", ""),
        conversation_turns=data.get("conversation_turns", []),
        active_plan=data.get("active_plan"),
        current_task=data.get("current_task", ""),
        recent_document_ids=data.get("recent_document_ids", []),
    )


class RedisSessionCache(ISessionCache):
    """
    Redis-backed short-term session memory.
    Uses the existing sync Redis client pattern from the project, wrapped
    in run_in_executor for async compatibility.
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(fn, *args, **kwargs))

    async def set(
        self,
        session_id: str,
        user_id: str,
        memory: ShortTermMemory,
        ttl_seconds: int = _DEFAULT_TTL,
    ) -> None:
        key = _make_key(user_id, session_id)
        serialized = _serialize(memory)

        def _set():
            self._redis.setex(key, ttl_seconds, serialized)

        await self._run(_set)
        logger.debug("session_memory_set", session_id=session_id, user_id=user_id, ttl=ttl_seconds)

    async def get(
        self,
        session_id: str,
        user_id: str,
    ) -> Optional[ShortTermMemory]:
        key = _make_key(user_id, session_id)

        def _get():
            raw = self._redis.get(key)
            return raw

        raw = await self._run(_get)
        if raw is None:
            logger.debug("session_memory_miss", session_id=session_id, user_id=user_id)
            return None

        raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        memory = _deserialize(raw_str)
        logger.debug("session_memory_hit", session_id=session_id, user_id=user_id)
        return memory

    async def delete(self, session_id: str, user_id: str) -> None:
        key = _make_key(user_id, session_id)
        await self._run(self._redis.delete, key)
        logger.info("session_memory_deleted", session_id=session_id, user_id=user_id)

    async def extend_ttl(self, session_id: str, user_id: str, ttl_seconds: int) -> None:
        key = _make_key(user_id, session_id)
        await self._run(self._redis.expire, key, ttl_seconds)
        logger.debug("session_memory_ttl_extended", session_id=session_id, ttl=ttl_seconds)

    async def exists(self, session_id: str, user_id: str) -> bool:
        key = _make_key(user_id, session_id)
        result = await self._run(self._redis.exists, key)
        return bool(result)
