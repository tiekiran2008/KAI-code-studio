"""
Repository Domain Entities
============================
Pydantic models for Repository, Branch, and AI-detected stack information.
Follows the existing Clean Architecture pattern used in workspace.py.
"""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RepositoryProvider(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    LOCAL = "local"


class IndexingStatus(str, Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    STALE = "stale"


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------

class LanguageStat(BaseModel):
    language: str
    percentage: float = 0.0
    bytes: int = 0


class DetectedStack(BaseModel):
    language: Optional[str] = None
    framework: Optional[str] = None
    package_manager: Optional[str] = None
    build_tool: Optional[str] = None
    test_framework: Optional[str] = None


class BranchInfo(BaseModel):
    name: str
    is_default: bool = False
    last_commit_sha: Optional[str] = None
    last_commit_message: Optional[str] = None
    last_commit_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Repository CRUD Models
# ---------------------------------------------------------------------------

class RepositoryCreate(BaseModel):
    url: str = Field(..., min_length=1, description="Repository URL or local path")
    provider: RepositoryProvider = RepositoryProvider.GITHUB
    name: Optional[str] = None
    description: Optional[str] = None
    default_branch: str = "main"
    workspace_id: Optional[str] = None
    git_access_token: Optional[str] = Field(None, description="PAT — stored encrypted server-side")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL must not be empty")
        return v


class RepositoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_branch: Optional[str] = None
    current_branch: Optional[str] = None
    workspace_id: Optional[str] = None
    git_access_token: Optional[str] = None


class RepositorySwitchBranch(BaseModel):
    branch: str = Field(..., min_length=1)


class Repository(BaseModel):
    id: str
    user_id: str
    workspace_id: Optional[str] = None
    url: str
    provider: RepositoryProvider = RepositoryProvider.GITHUB
    name: str
    description: Optional[str] = None
    owner: Optional[str] = None
    default_branch: str = "main"
    current_branch: str = "main"
    branches: List[str] = Field(default_factory=list)
    repo_size_kb: Optional[int] = None
    language_stats: List[LanguageStat] = Field(default_factory=list)
    detected_stack: Optional[DetectedStack] = None
    indexing_status: IndexingStatus = IndexingStatus.PENDING
    indexing_error: Optional[str] = None
    chunks_count: int = 0
    last_indexed_at: Optional[datetime] = None
    is_private: bool = False
    stars: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None  # NULL right after INSERT
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator("provider", mode="before")
    @classmethod
    def validate_provider(cls, v: Any) -> RepositoryProvider:
        if v is None:
            return RepositoryProvider.GITHUB
        if isinstance(v, RepositoryProvider):
            return v
        try:
            return RepositoryProvider(str(v).lower())
        except ValueError:
            return RepositoryProvider.GITHUB


class RepositoryHealthCheck(BaseModel):
    repo_id: str
    is_reachable: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    checked_at: datetime


class RepositoryListParams(BaseModel):
    workspace_id: Optional[str] = None
    provider: Optional[RepositoryProvider] = None
    indexing_status: Optional[IndexingStatus] = None
    search: Optional[str] = None
    skip: int = 0
    limit: int = 50
    sort_by: str = "updated_at"
    sort_dir: str = "desc"


class RepositoryIndexStatus(BaseModel):
    repository_id: str
    status: str
    stage: str
    progress: float = 0.0
    files_discovered: int = 0
    files_processed: int = 0
    chunks_created: int = 0
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class FileNode(BaseModel):
    id: str
    name: str
    path: str
    type: str = "file"  # "file" | "directory"
    size: Optional[int] = None
    language: Optional[str] = None
    children: Optional[List["FileNode"]] = None


class FileContentResponse(BaseModel):
    path: str
    name: str
    content: str
    size: int
    language: str
    is_binary: bool = False


