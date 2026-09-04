"""
Fix Suggestion Domain Entities
==============================
Strongly typed domain models for automated code fix suggestions.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class FixValidationStatus(str, Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"


class FixUserDecision(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class FixApplicationStatus(str, Enum):
    NOT_APPLIED = "not_applied"
    APPLYING = "applying"
    APPLIED = "applied"
    APPLY_FAILED = "apply_failed"
    STALE = "stale"


from src.domain.entities.verification import StaticVerificationResult
from src.domain.entities.sandbox import SandboxVerificationResult
from src.domain.entities.git import GitCommitResult, GitPushResult, GitPullRequestResult


class FixSuggestion(BaseModel):
    finding_index: int = Field(..., ge=0, description="Index of the review finding in the findings array")
    file_path: str = Field(..., min_length=1, description="Path to the target file")
    original_code: str = Field(..., min_length=1, description="Original source code snippet")
    proposed_code: str = Field(..., min_length=1, description="Proposed fixed code snippet")
    explanation: str = Field(..., min_length=1, description="Explanation of the fix")
    diff: str = Field(default="", description="Unified git diff representation")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    validation_status: FixValidationStatus = Field(
        default=FixValidationStatus.PENDING, description="Validation status of generated fix"
    )
    user_decision: FixUserDecision = Field(
        default=FixUserDecision.PENDING, description="User decision on the fix suggestion"
    )
    application_status: FixApplicationStatus = Field(
        default=FixApplicationStatus.NOT_APPLIED, description="Application status of the fix to workspace"
    )
    applied_at: Optional[str] = Field(
        default=None, description="ISO timestamp when the fix was successfully applied to workspace"
    )
    application_error: Optional[str] = Field(
        default=None, description="Safe error message if application failed or is stale"
    )
    previous_hash: Optional[str] = Field(
        default=None, description="SHA-256 hash of original file content before apply"
    )
    new_hash: Optional[str] = Field(
        default=None, description="SHA-256 hash of new file content after apply"
    )
    language: Optional[str] = Field(default=None, description="Programming language metadata")
    validation_message: Optional[str] = Field(default=None, description="Validation details or message")
    static_verification: Optional[StaticVerificationResult] = Field(
        default=None, description="Tier-1 static verification results"
    )
    test_verification: Optional[SandboxVerificationResult] = Field(
        default=None, description="Tier-2 isolated sandbox test verification results"
    )
    git_commit: Optional[GitCommitResult] = Field(
        default=None, description="Local Git commit metadata for this applied fix"
    )
    git_push: Optional[GitPushResult] = Field(
        default=None, description="Remote Git push metadata for this dedicated AI branch"
    )
    git_pull_request: Optional[GitPullRequestResult] = Field(
        default=None, description="GitHub Pull Request metadata for this pushed fix"
    )

    @field_validator("original_code", "proposed_code")
    @classmethod
    def _validate_non_empty_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Code snippet cannot be empty or whitespace only")
        return v

    @field_validator("file_path", "explanation")
    @classmethod
    def _validate_non_empty_string(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v
