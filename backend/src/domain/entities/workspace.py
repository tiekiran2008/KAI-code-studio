from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime

class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    default_ai_model: str = "gpt-4o"
    default_repo_id: Optional[str] = None
    vector_db_config: Dict[str, Any] = Field(default_factory=dict)
    tool_config: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("default_repo_id", mode="before")
    @classmethod
    def _coerce_empty_repo_id(cls, v: Optional[str]) -> Optional[str]:
        """Treat an empty string as None so the FK column stays NULL."""
        if v == "":
            return None
        return v

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_ai_model: Optional[str] = None
    default_repo_id: Optional[str] = None
    vector_db_config: Optional[Dict[str, Any]] = None
    tool_config: Optional[Dict[str, Any]] = None

class Workspace(WorkspaceBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None  # NULL right after INSERT; populated on first UPDATE
    repo_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)
