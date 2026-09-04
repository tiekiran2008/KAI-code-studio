"""
PostgreSQL Memory Repository
=============================
SQLAlchemy-backed implementation of ``IMemoryRepository``.

Design Decisions
----------------
* **Synchronous SQLAlchemy** is used (consistent with the existing codebase
  which uses a sync Session in dependencies.py). The ``run_in_executor``
  pattern wraps blocking calls so callers get ``async/await`` semantics.
* **Mapper functions** convert between domain entities and ORM rows —
  the domain layer never imports SQLAlchemy, preserving Clean Architecture.
* **Soft-delete** scrubs the `content` field and marks status=DELETED.
  The physical row is retained for audit/GDPR logging.
* **Optimistic concurrency** is enforced: update() checks the `version`
  column matches to prevent lost-update races between concurrent writers.
* **Tag search** uses JSON containment (PostgreSQL ``@>`` operator); for
  SQLite (unit tests) we fall back to a LIKE-based filter.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from functools import partial

from sqlalchemy.orm import Session

from src.domain.memory.entities import (
    BaseMemory,
    EpisodicMemory,
    EpisodeType,
    LongTermMemory,
    MemoryScore,
    MemoryStatus,
    MemoryType,
    RepositoryMemory,
    ShortTermMemory,
    UserPreferences,
    PreferredExplanationDepth,
)
from src.domain.memory.ports import IMemoryRepository
from src.infrastructure.memory.memory_encryptor import FernetMemoryEncryptor
from src.infrastructure.persistence.memory_models import DBMemory
from src.core.logger import logger


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------

def _row_to_entity(row: DBMemory, encryptor: FernetMemoryEncryptor) -> BaseMemory:
    """Convert a DBMemory ORM row to the appropriate domain entity."""
    content = row.content
    if row.content_encrypted and content:
        try:
            content = encryptor.decrypt(content)
        except ValueError:
            logger.warning("memory_decrypt_failed", memory_id=row.id)
            content = "[DECRYPTION ERROR]"

    score = MemoryScore(
        importance=row.importance,
        confidence=row.confidence,
        access_count=row.access_count,
        last_accessed=row.last_accessed or datetime.utcnow(),
        decay_factor=row.decay_factor,
        source=row.source,
        tags=row.tags_json or [],
    )

    common = dict(
        id=row.id,
        user_id=row.user_id,
        repository_id=row.repository_id,
        content=content,
        summary=row.summary or "",
        version=row.version,
        status=MemoryStatus(row.status),
        score=score,
        created_at=row.created_at,
        expires_at=row.expires_at,
        metadata=row.metadata_json or {},
    )

    mtype = MemoryType(row.memory_type)

    if mtype == MemoryType.SHORT_TERM:
        return ShortTermMemory(
            **common,
            memory_type=mtype,
            session_id=row.session_id or "",
            conversation_turns=row.conversation_turns or [],
            active_plan=row.active_plan_json,
            current_task=row.current_task or "",
            recent_document_ids=[],
        )

    if mtype == MemoryType.LONG_TERM:
        prefs_data = row.preferences_json or {}
        prefs = UserPreferences(
            preferred_languages=prefs_data.get("preferred_languages", []),
            preferred_frameworks=prefs_data.get("preferred_frameworks", []),
            preferred_testing_framework=prefs_data.get("preferred_testing_framework", ""),
            preferred_response_format=prefs_data.get("preferred_response_format", "markdown"),
            explanation_depth=PreferredExplanationDepth(
                prefs_data.get("explanation_depth", "standard")
            ),
            coding_conventions=prefs_data.get("coding_conventions", {}),
            frequently_accessed_repos=prefs_data.get("frequently_accessed_repos", []),
            frequently_asked_topics=prefs_data.get("frequently_asked_topics", []),
        )
        return LongTermMemory(
            **common,
            memory_type=mtype,
            preferences=prefs,
            fact=row.fact or "",
            topic=row.topic or "",
        )

    if mtype == MemoryType.REPOSITORY:
        return RepositoryMemory(
            **common,
            memory_type=mtype,
            repo_summary=row.repo_summary or "",
            architecture_summary=row.architecture_summary or "",
            module_summaries=row.module_summaries_json or {},
            dependency_summary=row.dependency_summary or "",
            frequently_referenced_files=row.frequently_ref_files or [],
            tech_stack=row.tech_stack_json or [],
            last_indexed_at=row.last_indexed_at,
        )

    # EPISODIC (default)
    return EpisodicMemory(
        **common,
        memory_type=mtype,
        episode_type=EpisodeType(row.episode_type or "general"),
        session_id=row.session_id or "",
        query=row.query or "",
        agent_outputs=row.agent_outputs_json or {},
        final_answer=row.final_answer or "",
        confidence_score=row.confidence_score or 0.0,
        citations=row.citations_json or [],
        execution_trace=row.execution_trace_json or [],
        lessons_learned=row.lessons_learned or "",
    )


def _entity_to_row(entity: BaseMemory, encryptor: FernetMemoryEncryptor) -> DBMemory:
    """Convert a domain entity to a DBMemory ORM row (new or updated)."""
    content = entity.content
    is_encrypted = False
    if encryptor.is_enabled and content:
        content = encryptor.encrypt(content)
        is_encrypted = True

    row = DBMemory(
        id=entity.id,
        user_id=entity.user_id,
        repository_id=entity.repository_id,
        memory_type=entity.memory_type.value,
        status=entity.status.value,
        version=entity.version,
        content=content,
        content_encrypted=is_encrypted,
        summary=entity.summary,
        importance=entity.score.importance,
        confidence=entity.score.confidence,
        access_count=entity.score.access_count,
        last_accessed=entity.score.last_accessed,
        decay_factor=entity.score.decay_factor,
        source=entity.score.source,
        tags_json=entity.score.tags,
        created_at=entity.created_at,
        updated_at=datetime.utcnow(),
        expires_at=entity.expires_at,
        metadata_json=entity.metadata,
    )

    if isinstance(entity, ShortTermMemory):
        row.session_id = entity.session_id
        row.conversation_turns = entity.conversation_turns
        row.active_plan_json = entity.active_plan
        row.current_task = entity.current_task

    elif isinstance(entity, LongTermMemory):
        prefs = entity.preferences
        row.preferences_json = {
            "preferred_languages": prefs.preferred_languages,
            "preferred_frameworks": prefs.preferred_frameworks,
            "preferred_testing_framework": prefs.preferred_testing_framework,
            "preferred_response_format": prefs.preferred_response_format,
            "explanation_depth": prefs.explanation_depth.value,
            "coding_conventions": prefs.coding_conventions,
            "frequently_accessed_repos": prefs.frequently_accessed_repos,
            "frequently_asked_topics": prefs.frequently_asked_topics,
        }
        row.fact = entity.fact
        row.topic = entity.topic

    elif isinstance(entity, RepositoryMemory):
        row.repo_summary = entity.repo_summary
        row.architecture_summary = entity.architecture_summary
        row.module_summaries_json = entity.module_summaries
        row.dependency_summary = entity.dependency_summary
        row.frequently_ref_files = entity.frequently_referenced_files
        row.tech_stack_json = entity.tech_stack
        row.last_indexed_at = entity.last_indexed_at

    elif isinstance(entity, EpisodicMemory):
        row.episode_type = entity.episode_type.value
        row.session_id = entity.session_id
        row.query = entity.query
        row.agent_outputs_json = entity.agent_outputs
        row.final_answer = entity.final_answer
        row.confidence_score = entity.confidence_score
        row.citations_json = entity.citations
        row.execution_trace_json = entity.execution_trace
        row.lessons_learned = entity.lessons_learned

    return row


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------

class PostgresMemoryRepository(IMemoryRepository):
    """
    SQLAlchemy implementation of IMemoryRepository targeting PostgreSQL.

    All public methods are async; blocking DB calls run in the default
    thread-pool executor via asyncio.get_event_loop().run_in_executor.
    """

    def __init__(
        self,
        session: Session,
        encryptor: Optional[FernetMemoryEncryptor] = None,
    ) -> None:
        self._session = session
        self._enc = encryptor or FernetMemoryEncryptor()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _run(self, fn, *args, **kwargs):
        """Run a synchronous callable in the thread-pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(fn, *args, **kwargs))

    def _get_row(self, memory_id: str, user_id: str) -> Optional[DBMemory]:
        row = self._session.query(DBMemory).filter_by(id=memory_id).first()
        if row is None:
            return None
        if row.user_id != user_id:
            raise PermissionError(
                f"Memory {memory_id} does not belong to user {user_id}"
            )
        return row

    # ------------------------------------------------------------------
    # IMemoryRepository implementation
    # ------------------------------------------------------------------

    async def save(self, memory: BaseMemory) -> BaseMemory:
        def _save():
            row = _entity_to_row(memory, self._enc)
            self._session.add(row)
            self._session.commit()
            self._session.refresh(row)
            logger.info("memory_created", memory_id=row.id, memory_type=row.memory_type)
            return _row_to_entity(row, self._enc)

        return await self._run(_save)

    async def update(self, memory: BaseMemory) -> BaseMemory:
        def _update():
            row = self._get_row(memory.id, memory.user_id)
            if row is None:
                raise ValueError(f"Memory {memory.id} not found")

            # Optimistic concurrency check
            if row.version != memory.version - 1:
                raise ValueError(
                    f"Concurrent modification conflict: expected version "
                    f"{memory.version - 1}, found {row.version}"
                )

            updated = _entity_to_row(memory, self._enc)
            for col in DBMemory.__table__.columns:
                if col.name not in ("id", "created_at"):
                    setattr(row, col.name, getattr(updated, col.name))

            self._session.commit()
            self._session.refresh(row)
            logger.info("memory_updated", memory_id=row.id, version=row.version)
            return _row_to_entity(row, self._enc)

        return await self._run(_update)

    async def get_by_id(self, memory_id: str, user_id: str) -> Optional[BaseMemory]:
        def _get():
            row = self._get_row(memory_id, user_id)
            return _row_to_entity(row, self._enc) if row else None

        return await self._run(_get)

    async def list_by_user(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        repository_id: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BaseMemory]:
        def _list():
            q = self._session.query(DBMemory).filter(DBMemory.user_id == user_id)
            if memory_type:
                q = q.filter(DBMemory.memory_type == memory_type.value)
            if repository_id:
                q = q.filter(DBMemory.repository_id == repository_id)
            if not include_archived:
                q = q.filter(DBMemory.status.in_(["active"]))
            rows = q.order_by(DBMemory.last_accessed.desc()).limit(limit).offset(offset).all()
            return [_row_to_entity(r, self._enc) for r in rows]

        return await self._run(_list)

    async def search_by_tags(
        self,
        user_id: str,
        tags: List[str],
        memory_type: Optional[MemoryType] = None,
        limit: int = 20,
    ) -> List[BaseMemory]:
        def _search():
            q = self._session.query(DBMemory).filter(
                DBMemory.user_id == user_id,
                DBMemory.status == "active",
            )
            if memory_type:
                q = q.filter(DBMemory.memory_type == memory_type.value)
            # JSON containment — works in PostgreSQL; degrades gracefully in SQLite
            rows = q.all()
            tag_set = set(tags)
            filtered = [r for r in rows if tag_set.issubset(set(r.tags_json or []))]
            return [_row_to_entity(r, self._enc) for r in filtered[:limit]]

        return await self._run(_search)

    async def soft_delete(self, memory_id: str, user_id: str) -> None:
        def _soft():
            row = self._get_row(memory_id, user_id)
            if row is None:
                return
            row.status = "deleted"
            row.content = "[GDPR ERASED]"
            row.content_encrypted = False
            row.summary = "[DELETED]"
            row.updated_at = datetime.utcnow()
            self._session.commit()
            logger.info("memory_soft_deleted", memory_id=memory_id, user_id=user_id)

        await self._run(_soft)

    async def hard_delete(self, memory_id: str, user_id: str) -> None:
        def _hard():
            row = self._get_row(memory_id, user_id)
            if row:
                self._session.delete(row)
                self._session.commit()
                logger.info("memory_hard_deleted", memory_id=memory_id, user_id=user_id)

        await self._run(_hard)

    async def hard_delete_all_for_user(self, user_id: str) -> int:
        def _delete_all():
            count = (
                self._session.query(DBMemory)
                .filter(DBMemory.user_id == user_id)
                .delete(synchronize_session=False)
            )
            self._session.commit()
            logger.info("memory_gdpr_erasure", user_id=user_id, count=count)
            return count

        return await self._run(_delete_all)

    async def get_expired(self, limit: int = 100) -> List[BaseMemory]:
        def _expired():
            now = datetime.utcnow()
            rows = (
                self._session.query(DBMemory)
                .filter(
                    DBMemory.expires_at != None,  # noqa: E711
                    DBMemory.expires_at < now,
                    DBMemory.status == "active",
                )
                .limit(limit)
                .all()
            )
            return [_row_to_entity(r, self._enc) for r in rows]

        return await self._run(_expired)

    async def get_inactive(self, days_inactive: int = 90, limit: int = 200) -> List[BaseMemory]:
        from datetime import timedelta

        def _inactive():
            threshold = datetime.utcnow() - timedelta(days=days_inactive)
            rows = (
                self._session.query(DBMemory)
                .filter(
                    DBMemory.last_accessed < threshold,
                    DBMemory.status == "active",
                )
                .limit(limit)
                .all()
            )
            return [_row_to_entity(r, self._enc) for r in rows]

        return await self._run(_inactive)

    async def update_score(self, memory_id: str, score_delta: Dict[str, Any]) -> None:
        def _score():
            row = (
                self._session.query(DBMemory).filter(DBMemory.id == memory_id).first()
            )
            if row is None:
                return
            if "access_count" in score_delta:
                row.access_count = score_delta["access_count"]
            if "last_accessed" in score_delta:
                row.last_accessed = score_delta["last_accessed"]
            if "decay_factor" in score_delta:
                row.decay_factor = score_delta["decay_factor"]
            row.updated_at = datetime.utcnow()
            self._session.commit()

        await self._run(_score)
