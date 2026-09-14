"""
Project Domain Entities
========================
Pydantic models for Projects (logical groupings of multiple repositories).
"""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime

from src.domain.entities.repository import Repository


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    workspace_id: Optional[str] = None
    repository_ids: List[str] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    workspace_id: Optional[str] = None


class Project(BaseModel):
    id: str
    user_id: str
    workspace_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    repositories: List[Repository] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> ProjectStatus:
        if isinstance(v, ProjectStatus):
            return v
        if not v:
            return ProjectStatus.ACTIVE
        normalized = str(v).strip().lower()
        if normalized == "archived":
            return ProjectStatus.ARCHIVED
        return ProjectStatus.ACTIVE

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, v: Any) -> datetime:
        if v is None:
            return datetime.utcnow()
        return v

    @field_validator("updated_at", mode="before")
    @classmethod
    def validate_updated_at(cls, v: Any) -> datetime:
        if v is None:
            return datetime.utcnow()
        return v

    model_config = ConfigDict(from_attributes=True)


class ProjectDashboard(BaseModel):
    project: Project
    total_repositories: int
    indexed_repositories: int
    failed_repositories: int
    total_chunks: int
    languages: List[str]
