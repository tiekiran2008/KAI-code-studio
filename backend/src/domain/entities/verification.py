"""
Static Verification Domain Entities
===================================
Strongly typed domain models for Tier-1 in-memory static & syntax verification.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"
    SOURCE_CHANGED = "source_changed"


class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"


class VerificationCheck(BaseModel):
    name: str = Field(..., description="Name of the deterministic check (e.g. non_empty_source, syntax_parser)")
    status: CheckStatus = Field(..., description="Result status of this individual check")
    message: str = Field(..., description="Safe, descriptive summary of check execution")
    line_number: Optional[int] = Field(default=None, description="1-indexed line number if an error was detected")
    column: Optional[int] = Field(default=None, description="1-indexed column offset if an error was detected")


class StaticVerificationResult(BaseModel):
    status: VerificationStatus = Field(
        default=VerificationStatus.NOT_RUN,
        description="Overall Tier-1 verification status",
    )
    language: Optional[str] = Field(
        default=None,
        description="Identified or detected programming language",
    )
    verified_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when verification was executed",
    )
    verified_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of the verified file content",
    )
    duration_ms: Optional[int] = Field(
        default=None,
        description="Duration of in-memory verification in milliseconds",
    )
    checks: List[VerificationCheck] = Field(
        default_factory=list,
        description="List of individual checks executed",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Safe error messages if checks failed",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal warnings detected during verification",
    )
    message: Optional[str] = Field(
        default=None,
        description="High-level human-readable verification summary",
    )
