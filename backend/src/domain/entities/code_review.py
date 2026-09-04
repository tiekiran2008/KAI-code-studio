from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.domain.entities.fix_suggestion import FixSuggestion, FixValidationStatus, FixUserDecision


class SeverityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ReviewStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ReviewFinding(BaseModel):
    issue: str
    severity: SeverityEnum
    explanation: str
    suggested_fix: Optional[str] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    fix_suggestion: Optional[FixSuggestion] = None

class CodeReviewBase(BaseModel):
    repository_id: str

class CodeReviewCreate(CodeReviewBase):
    pass

class CodeReview(CodeReviewBase):
    id: str
    user_id: str
    status: ReviewStatusEnum
    progress_percent: Optional[int] = 0
    current_stage: Optional[str] = "queued"
    progress_message: Optional[str] = None
    findings: List[ReviewFinding] = Field(default_factory=list)

    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    duration_ms: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
