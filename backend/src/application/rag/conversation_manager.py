"""
Conversation Manager
====================
Redis-backed session store that persists, retrieves, and manages
conversation turns for multi-turn RAG interactions.

Features:
- Stores up to MAX_TURNS (default: 10) recent turns per session.
- Serialises ConversationHistory as JSON in Redis.
- Auto-expires sessions after settings.CONVERSATION_TTL_SECONDS.
- Provides safe read/write with graceful degradation (no Redis = stateless).
- Thread-safe; designed for async FastAPI usage via asyncio.to_thread.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

import redis

from src.domain.models.rag import (
    ConversationHistory,
    ConversationTurn,
    ConversationRole,
)
from src.core.config import settings
from src.core.logger import logger

_MAX_TURNS = 10
_KEY_PREFIX = "rag:session:"


def _session_key(session_id: str) -> str:
    return f"{_KEY_PREFIX}{session_id}"


def _serialise(history: ConversationHistory) -> str:
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

    data = {
        "session_id": history.session_id,
        "repo_id": history.repo_id,
        "created_at": history.created_at.isoformat(),
        "updated_at": history.updated_at.isoformat(),
        "turns": [
            {
                "role": t.role.value,
                "content": t.content,
                "timestamp": t.timestamp.isoformat(),
                "metadata": t.metadata,
            }
            for t in history.turns
        ],
    }
    return json.dumps(data, default=default)


def _deserialise(raw: str) -> ConversationHistory:
    data = json.loads(raw)
    turns = [
        ConversationTurn(
            role=ConversationRole(t["role"]),
            content=t["content"],
            timestamp=datetime.fromisoformat(t["timestamp"]),
            metadata=t.get("metadata", {}),
        )
        for t in data.get("turns", [])
    ]
    return ConversationHistory(
        session_id=data["session_id"],
        repo_id=data["repo_id"],
        turns=turns,
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


class ConversationManager:
    """Manages conversation sessions backed by Redis."""

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, repo_id: str) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        history = ConversationHistory(session_id=session_id, repo_id=repo_id)
        self._save(history)
        return session_id

    def get_or_create(self, session_id: Optional[str], repo_id: str) -> ConversationHistory:
        """Retrieve an existing session or create a new one."""
        if session_id:
            history = self.get_session(session_id)
            if history:
                return history
        new_id = session_id or str(uuid.uuid4())
        history = ConversationHistory(session_id=new_id, repo_id=repo_id)
        self._save(history)
        return history

    def get_session(self, session_id: str) -> Optional[ConversationHistory]:
        """Return the ConversationHistory for a session, or None if not found."""
        try:
            raw = self._redis.get(_session_key(session_id))
            if raw is None:
                return None
            return _deserialise(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        except Exception as exc:
            logger.warning("conversation_get_failed", session_id=session_id, error=str(exc))
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found."""
        try:
            deleted = self._redis.delete(_session_key(session_id))
            return deleted > 0
        except Exception as exc:
            logger.warning("conversation_delete_failed", session_id=session_id, error=str(exc))
            return False

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------

    def add_user_turn(self, history: ConversationHistory, content: str) -> None:
        """Append a user turn and persist the session."""
        history.turns.append(
            ConversationTurn(role=ConversationRole.USER, content=content)
        )
        self._trim_and_save(history)

    def add_assistant_turn(
        self, history: ConversationHistory, content: str, metadata: dict = None
    ) -> None:
        """Append an assistant turn and persist the session."""
        history.turns.append(
            ConversationTurn(
                role=ConversationRole.ASSISTANT,
                content=content,
                metadata=metadata or {},
            )
        )
        self._trim_and_save(history)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _trim_and_save(self, history: ConversationHistory) -> None:
        """Keep only the last _MAX_TURNS turns, then save."""
        if len(history.turns) > _MAX_TURNS:
            history.turns = history.turns[-_MAX_TURNS:]
        history.updated_at = datetime.utcnow()
        self._save(history)

    def _save(self, history: ConversationHistory) -> None:
        try:
            self._redis.setex(
                _session_key(history.session_id),
                settings.CONVERSATION_TTL_SECONDS,
                _serialise(history),
            )
        except Exception as exc:
            logger.warning(
                "conversation_save_failed",
                session_id=history.session_id,
                error=str(exc),
            )
