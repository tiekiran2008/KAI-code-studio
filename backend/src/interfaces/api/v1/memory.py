"""
Memory API Router
=================
FastAPI endpoints for the Phase 7 Intelligent Memory & Context Management system.

Endpoints
---------
POST   /memory/search                   Semantic memory search
GET    /memory/                         List memories (paginated)
GET    /memory/{memory_id}              Get a single memory
POST   /memory/episodic                 Create episodic memory manually
POST   /memory/long-term                Create a long-term fact memory
POST   /memory/repository               Create a repository knowledge record
PATCH  /memory/{memory_id}              Update a memory
PUT    /memory/preferences              Update user preferences
DELETE /memory/{memory_id}              Soft-delete a memory
DELETE /memory/{memory_id}/hard         Hard-delete (GDPR physical erasure)
DELETE /memory/users/{user_id}/all      GDPR right-to-erasure for all user memories
POST   /memory/consolidate              Trigger manual consolidation run
GET    /memory/metrics                  Memory subsystem metrics

Security
--------
Every endpoint enforces user isolation via the `X-User-ID` header.
In a production deployment this would be replaced with a JWT-based auth
dependency from the existing auth middleware.
"""
from __future__ import annotations

import time
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from src.application.services.memory_service import MemoryService
from src.domain.memory.entities import (
    EpisodicMemory,
    EpisodeType,
    LongTermMemory,
    MemoryScore,
    MemorySearchQuery,
    MemoryType,
    RepositoryMemory,
)
from src.interfaces.api.v1.schemas.memory import (
    ConsolidationReportSchema,
    CreateEpisodicMemoryRequest,
    CreateLongTermMemoryRequest,
    CreateRepositoryMemoryRequest,
    ForgetMemoryResponse,
    ForgetUserResponse,
    MemoryListResponse,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResultItem,
    MemoryScoreSchema,
    UpdateMemoryRequest,
    UpdatePreferencesRequest,
)
from src.interfaces.api.dependencies import get_memory_service
from src.core.logger import logger

router = APIRouter()


# ---------------------------------------------------------------------------
# Header-based user isolation (placeholder for JWT middleware)
# ---------------------------------------------------------------------------

def _require_user_id(x_user_id: Optional[str] = Header(None, alias="X-User-ID")) -> str:
    """Enforce user isolation via X-User-ID header.

    Returns 401 (not 422) when the header is absent or blank, so clients
    see a consistent authentication error rather than a validation error.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-ID header is required for memory operations.",
        )
    return x_user_id.strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entity_to_schema(entity) -> MemoryResponse:
    score = entity.score
    return MemoryResponse(
        id=entity.id,
        user_id=entity.user_id,
        repository_id=entity.repository_id,
        memory_type=entity.memory_type.value,
        content=entity.content,
        summary=entity.summary,
        version=entity.version,
        status=entity.status.value,
        score=MemoryScoreSchema(
            importance=score.importance,
            confidence=score.confidence,
            access_count=score.access_count,
            last_accessed=score.last_accessed,
            decay_factor=score.decay_factor,
            source=score.source,
            tags=score.tags,
        ),
        created_at=entity.created_at,
        expires_at=entity.expires_at,
        metadata=entity.metadata,
    )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.post(
    "/search",
    response_model=MemorySearchResponse,
    summary="Semantic memory search",
    description=(
        "Performs a multi-store semantic search across long-term, repository, "
        "and episodic memories. Returns ranked results within the caller's user scope."
    ),
)
async def search_memories(
    request: MemorySearchRequest,
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> MemorySearchResponse:
    t0 = time.perf_counter()
    try:
        memory_types = [MemoryType(t) for t in request.memory_types] if request.memory_types else list(MemoryType)
        query = MemorySearchQuery(
            query_text=request.query,
            user_id=user_id,
            memory_types=memory_types,
            repository_id=request.repository_id,
            session_id=request.session_id,
            tags=request.tags,
            top_k=request.top_k,
            min_score=request.min_score,
        )
        results = await svc.search(query)
        latency_ms = (time.perf_counter() - t0) * 1000

        items = [
            MemorySearchResultItem(
                memory=_entity_to_schema(r.memory),
                relevance_score=r.relevance_score,
                rank=r.rank,
            )
            for r in results
        ]
        return MemorySearchResponse(
            results=items,
            total=len(items),
            query=request.query,
            latency_ms=round(latency_ms, 2),
        )
    except Exception as exc:
        logger.error("memory_search_api_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=MemoryListResponse,
    summary="List memories (paginated)",
)
async def list_memories(
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    repository_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> MemoryListResponse:
    try:
        mtype = MemoryType(memory_type) if memory_type else None
        memories = await svc.list_memories(
            user_id=user_id,
            memory_type=mtype,
            repository_id=repository_id,
            limit=limit,
            offset=offset,
        )
        return MemoryListResponse(
            memories=[_entity_to_schema(m) for m in memories],
            total=len(memories),
            offset=offset,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------------

@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get a single memory by ID",
)
async def get_memory(
    memory_id: str,
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    entity = await svc.get_memory(memory_id, user_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
    return _entity_to_schema(entity)


# ---------------------------------------------------------------------------
# Create — Episodic
# ---------------------------------------------------------------------------

@router.post(
    "/episodic",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an episodic memory manually",
)
async def create_episodic_memory(
    request: CreateEpisodicMemoryRequest,
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    try:
        episode = await svc.save_episode(
            user_id=user_id,
            session_id=request.session_id,
            query=request.query,
            repository_id=request.repository_id,
            agent_outputs={},
            final_answer=request.final_answer or request.content,
            confidence_score=request.confidence_score,
            citations=[],
            execution_trace=[],
            episode_type=EpisodeType(request.episode_type),
        )
        return _entity_to_schema(episode)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Create — Long-term fact
# ---------------------------------------------------------------------------

@router.post(
    "/long-term",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a long-term fact or preference memory",
)
async def create_long_term_memory(
    request: CreateLongTermMemoryRequest,
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    try:
        from src.domain.memory.entities import UserPreferences
        memory = LongTermMemory(
            user_id=user_id,
            repository_id=request.repository_id,
            memory_type=MemoryType.LONG_TERM,
            content=request.content,
            summary=request.summary or request.content[:100],
            topic=request.topic,
            preferences=UserPreferences(),
            score=MemoryScore(
                importance=request.importance,
                tags=request.tags,
                source="user_explicit",
            ),
        )
        saved = await svc._mgr.create_long_term(user_id, memory)
        return _entity_to_schema(saved)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Create — Repository memory
# ---------------------------------------------------------------------------

@router.post(
    "/repository",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a repository knowledge memory",
)
async def create_repository_memory(
    request: CreateRepositoryMemoryRequest,
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    try:
        memory = RepositoryMemory(
            user_id=user_id,
            repository_id=request.repository_id,
            memory_type=MemoryType.REPOSITORY,
            content=request.repo_summary or request.architecture_summary,
            summary=f"Repository knowledge: {request.repository_id}",
            repo_summary=request.repo_summary,
            architecture_summary=request.architecture_summary,
            dependency_summary=request.dependency_summary,
            tech_stack=request.tech_stack,
            score=MemoryScore(tags=request.tags, importance=0.8, source="system"),
        )
        saved = await svc._mgr.create_repository_memory(user_id, memory)
        return _entity_to_schema(saved)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.patch(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Partial update of a memory",
)
async def update_memory(
    memory_id: str,
    request: UpdateMemoryRequest,
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    try:
        updates = request.model_dump(exclude_none=True)
        updated = await svc._mgr.update_memory(memory_id, user_id, updates)
        return _entity_to_schema(updated)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# User preferences
# ---------------------------------------------------------------------------

@router.put(
    "/preferences",
    response_model=MemoryResponse,
    summary="Update user coding preferences (long-term memory)",
)
async def update_preferences(
    request: UpdatePreferencesRequest,
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    try:
        updated = await svc.update_user_preferences(
            user_id=user_id,
            preferences_update=request.preferences.model_dump(),
        )
        return _entity_to_schema(updated)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Soft delete (GDPR-lite)
# ---------------------------------------------------------------------------

@router.delete(
    "/{memory_id}",
    response_model=ForgetMemoryResponse,
    summary="Soft-delete a memory (GDPR-compliant PII scrubbing)",
)
async def forget_memory(
    memory_id: str,
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> ForgetMemoryResponse:
    try:
        await svc.forget_memory(memory_id, user_id, hard=False)
        return ForgetMemoryResponse(
            success=True,
            memory_id=memory_id,
            message="Memory soft-deleted. Content scrubbed per GDPR.",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Hard delete (GDPR erasure)
# ---------------------------------------------------------------------------

@router.delete(
    "/{memory_id}/hard",
    response_model=ForgetMemoryResponse,
    summary="Hard-delete a memory (physical row removal — GDPR Article 17)",
)
async def hard_forget_memory(
    memory_id: str,
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> ForgetMemoryResponse:
    try:
        await svc.forget_memory(memory_id, user_id, hard=True)
        return ForgetMemoryResponse(
            success=True,
            memory_id=memory_id,
            message="Memory physically deleted from all stores.",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GDPR right-to-erasure — delete all memories for a user
# ---------------------------------------------------------------------------

@router.delete(
    "/users/{target_user_id}/all",
    response_model=ForgetUserResponse,
    summary="GDPR right-to-erasure: delete ALL memories for a user",
)
async def forget_all_user_memories(
    target_user_id: str,
    requesting_user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> ForgetUserResponse:
    # Only allow self-erasure or admin (extend with role check in production)
    if requesting_user_id != target_user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only erase your own memories.",
        )
    try:
        count = await svc.forget_user(target_user_id)
        return ForgetUserResponse(
            success=True,
            user_id=target_user_id,
            total_deleted=count,
            message=f"All {count} memories for user {target_user_id} have been permanently deleted.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Manual consolidation trigger
# ---------------------------------------------------------------------------

@router.post(
    "/consolidate",
    response_model=ConsolidationReportSchema,
    summary="Trigger a manual memory consolidation run",
)
async def trigger_consolidation(
    user_id: str = Depends(_require_user_id),
    svc: MemoryService = Depends(get_memory_service),
) -> ConsolidationReportSchema:
    try:
        report = await svc._mgr.consolidate()
        return ConsolidationReportSchema(
            run_id=report.run_id,
            memories_scanned=report.memories_scanned,
            memories_merged=report.memories_merged,
            memories_archived=report.memories_archived,
            memories_deleted=report.memories_deleted,
            duration_ms=report.duration_ms,
            errors=report.errors,
            ran_at=report.ran_at,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
