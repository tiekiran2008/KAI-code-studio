"""
Sandbox Verification Domain Entities
====================================
Strongly typed domain models for Tier-2 isolated ephemeral container verification.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SandboxVerificationStatusEnum(str, Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    SANDBOX_UNAVAILABLE = "sandbox_unavailable"
    EXECUTION_ERROR = "execution_error"
    UNSUPPORTED = "unsupported"


class SandboxExecutionRequest(BaseModel):
    workspace_root: str = Field(..., min_length=1, description="Absolute path to the local repository workspace")
    verification_type: str = Field(default="isolated_tests", description="Type of Tier-2 verification")
    language: str = Field(default="Python", description="Programming language of the target repository")
    framework: str = Field(default="pytest", description="Test framework to execute")
    timeout_seconds: int = Field(default=30, ge=5, le=60, description="Execution timeout limit in seconds")
    relative_target_path: Optional[str] = Field(default=None, description="Optional relative path to target test file")
    repository_id: Optional[str] = Field(default=None, description="Identifier of the repository")
    review_id: Optional[str] = Field(default=None, description="Identifier of the code review")
    finding_index: Optional[int] = Field(default=None, ge=0, description="Index of the finding")


class SandboxVerificationResult(BaseModel):
    status: SandboxVerificationStatusEnum = Field(
        default=SandboxVerificationStatusEnum.NOT_RUN,
        description="Overall Tier-2 sandbox verification status",
    )
    verification_type: str = Field(
        default="isolated_tests",
        description="Type of verification executed",
    )
    test_framework: str = Field(
        default="pytest",
        description="Test framework used during execution",
    )
    command_label: str = Field(
        default="pytest -q",
        description="Safe, human-readable command representation",
    )
    exit_code: Optional[int] = Field(
        default=None,
        description="Process exit code from container execution",
    )
    duration_ms: int = Field(
        default=0,
        ge=0,
        description="Execution duration in milliseconds",
    )
    tests_total: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total number of tests discovered/executed",
    )
    tests_passed: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of passing tests",
    )
    tests_failed: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of failing tests",
    )
    tests_skipped: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of skipped tests",
    )
    stdout_summary: str = Field(
        default="",
        description="Bounded, sanitized stdout capture (max 64KB)",
    )
    stderr_summary: str = Field(
        default="",
        description="Bounded, sanitized stderr capture (max 64KB)",
    )
    timed_out: bool = Field(
        default=False,
        description="True if execution exceeded timeout limit and was killed",
    )
    resource_limit_hit: bool = Field(
        default=False,
        description="True if container hit memory or PID limits",
    )
    verified_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when verification was executed",
    )
    verified_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of verified source state",
    )
    message: Optional[str] = Field(
        default=None,
        description="High-level verification status summary message",
    )
    error_details: Optional[str] = Field(
        default=None,
        description="Detailed diagnostic or error summary if execution failed",
    )
