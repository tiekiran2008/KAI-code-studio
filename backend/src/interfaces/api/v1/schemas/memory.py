"""
Memory API Schemas
==================
Pydantic request/response models for the /api/v1/memory endpoints.

Design: schemas are kept separate from domain entities so the API contract
can evolve independently of internal domain models.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared / embedded
# ---------------------------------------------------------------------------

class MemoryScoreSchema(BaseModel):
    importance:    float = Field(0.5, ge=0.0, le=1.0)
    confidence:    float = Field(0.8, ge=0.0, le=1.0)
    access_count:  int   = 0
    last_accessed: Optional[datetime] = None
    decay_factor:  float = 1.0
    source:        str   = "system"
    tags:          List[str] = []


class UserPreferencesSchema(BaseModel):
    preferred_languages:         List[str] = []
    preferred_frameworks:        List[str] = []
    preferred_testing_framework: str = ""
    preferred_response_format:   str = "markdown"
    explanation_depth:           str = "standard"
    coding_conventions:          Dict[str, str] = {}
    frequently_accessed_repos:   List[str] = []
    frequently_asked_topics:     List[str] = []


# ---------------------------------------------------------------------------
# Memory response (generic — all types)
# ---------------------------------------------------------------------------

class MemoryResponse(BaseModel):
    id:            str
    user_id:       str
    repository_id: Optional[str] = None
    memory_type:   str
    content:       str
    summary:       str
    version:       int
    status:        str
    score:         MemoryScoreSchema
    created_at:    datetime
    expires_at:    Optional[datetime] = None
    metadata:      Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class MemorySearchRequest(BaseModel):
    query:         str = Field(..., min_length=1, max_length=2000)
    memory_types:  List[str] = Field(default=[], description="Filter by memory type(s)")
    repository_id: Optional[str] = None
    session_id:    Optional[str] = None
    tags:          List[str] = []
    top_k:         int = Field(5, ge=1, le=50)
    min_score:     float = Field(0.0, ge=0.0, le=1.0)


class MemorySearchResultItem(BaseModel):
    memory:          MemoryResponse
    relevance_score: float
    rank:            int


class MemorySearchResponse(BaseModel):
    results:       List[MemorySearchResultItem]
    total:         int
    query:         str
    latency_ms:    float


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class CreateEpisodicMemoryRequest(BaseModel):
    session_id:     str
    query:          str = Field(..., min_length=1)
    repository_id:  Optional[str] = None
    episode_type:   str = "general"
    content:        str = ""
    final_answer:   str = ""
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    tags:           List[str] = []


class CreateLongTermMemoryRequest(BaseModel):
    content:        str = Field(..., min_length=1)
    summary:        str = ""
    repository_id:  Optional[str] = None
    topic:          str = ""
    tags:           List[str] = []
    importance:     float = Field(0.5, ge=0.0, le=1.0)


class CreateRepositoryMemoryRequest(BaseModel):
    repository_id:        str
    repo_summary:         str = ""
    architecture_summary: str = ""
    dependency_summary:   str = ""
    tech_stack:           List[str] = []
    tags:                 List[str] = []


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

class UpdateMemoryRequest(BaseModel):
    content:    Optional[str] = None
    summary:    Optional[str] = None
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags:       Optional[List[str]] = None
    metadata:   Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

class UpdatePreferencesRequest(BaseModel):
    preferences: UserPreferencesSchema


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

class MemoryListResponse(BaseModel):
    memories:    List[MemoryResponse]
    total:       int
    offset:      int
    limit:       int


# ---------------------------------------------------------------------------
# GDPR
# ---------------------------------------------------------------------------

class ForgetMemoryResponse(BaseModel):
    success:    bool
    memory_id:  Optional[str] = None
    message:    str


class ForgetUserResponse(BaseModel):
    success:    bool
    user_id:    str
    total_deleted: int
    message:    str


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------

class ConsolidationReportSchema(BaseModel):
    run_id:            str
    memories_scanned:  int
    memories_merged:   int
    memories_archived: int
    memories_deleted:  int
    duration_ms:       float
    errors:            List[str]
    ran_at:            datetime
