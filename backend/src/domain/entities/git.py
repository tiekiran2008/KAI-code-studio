"""
Git Domain Entities
===================
Strongly typed domain models for local Git working tree operations,
branch management, and targeted fix commit results.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class GitCommitStatusEnum(str, Enum):
    COMMITTED = "committed"
    ALREADY_COMMITTED = "already_committed"
    STALE_SOURCE = "stale_source"
    NOT_GIT_REPOSITORY = "not_git_repository"
    DIRTY_CONFLICT = "dirty_conflict"
    FAILED = "failed"


class GitPushStatusEnum(str, Enum):
    PUSHED = "pushed"
    ALREADY_PUSHED = "already_pushed"
    NO_REMOTE = "no_remote"
    REMOTE_MISMATCH = "remote_mismatch"
    GIT_STATE_CHANGED = "git_state_changed"
    AUTH_REQUIRED = "auth_required"
    PUSH_REJECTED = "push_rejected"
    REMOTE_UNAVAILABLE = "remote_unavailable"
    FAILED = "failed"


class WorkingTreeStatus(BaseModel):
    """Snapshot of a local repository's Git working tree."""
    is_git_repo: bool = Field(default=False, description="True if workspace contains a valid .git repository")
    current_branch: Optional[str] = Field(default=None, description="Active branch name or HEAD")
    head_commit_sha: Optional[str] = Field(default=None, description="Latest commit SHA on active branch")
    modified_files: List[str] = Field(default_factory=list, description="Unstaged modified files in working tree")
    staged_files: List[str] = Field(default_factory=list, description="Staged files in the Git index")
    untracked_files: List[str] = Field(default_factory=list, description="Untracked files in workspace")


class GitCommitResult(BaseModel):
    """Result of an isolated fix commit operation."""
    status: GitCommitStatusEnum = Field(..., description="Commit execution status")
    branch_name: Optional[str] = Field(default=None, description="Dedicated AI fix branch name")
    commit_sha: Optional[str] = Field(default=None, description="Created commit object SHA-1")
    committed_at: Optional[str] = Field(default=None, description="ISO timestamp when commit was created")
    file_path: Optional[str] = Field(default=None, description="Relative path of the committed fix target")
    commit_message: Optional[str] = Field(default=None, description="Deterministic commit message")
    base_branch: Optional[str] = Field(default=None, description="Base branch commit was branched from")
    base_commit_sha: Optional[str] = Field(default=None, description="Base commit SHA")
    message: Optional[str] = Field(default=None, description="Informational message or reason")
    error_details: Optional[str] = Field(default=None, description="Safe error details on failure")


class GitPushResult(BaseModel):
    """Result of an isolated AI fix branch push operation."""
    status: GitPushStatusEnum = Field(..., description="Push execution status")
    remote_name: Optional[str] = Field(default="origin", description="Git remote name pushed to")
    branch_name: Optional[str] = Field(default=None, description="Dedicated AI fix branch pushed")
    commit_sha: Optional[str] = Field(default=None, description="Commit SHA verified and pushed")
    remote_url_masked: Optional[str] = Field(default=None, description="Masked URL of remote (no secrets/tokens)")
    pushed_at: Optional[str] = Field(default=None, description="ISO timestamp when push completed")
    message: Optional[str] = Field(default=None, description="Informational message or summary")
    error_details: Optional[str] = Field(default=None, description="Safe error details on failure (no secrets)")


class GitPullRequestStatusEnum(str, Enum):
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"
    AUTH_REQUIRED = "auth_required"
    PERMISSION_DENIED = "permission_denied"
    REMOTE_BRANCH_MISSING = "remote_branch_missing"
    GIT_STATE_CHANGED = "git_state_changed"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class GitPullRequestResult(BaseModel):
    """Result of a GitHub Pull Request creation operation."""
    status: GitPullRequestStatusEnum = Field(..., description="PR creation execution status")
    pr_number: Optional[int] = Field(default=None, description="Created or reconciled PR number")
    pr_url: Optional[str] = Field(default=None, description="Trusted GitHub HTML URL for the pull request")
    title: Optional[str] = Field(default=None, description="Pull request title")
    body: Optional[str] = Field(default=None, description="Pull request body/description")
    head_branch: Optional[str] = Field(default=None, description="Head branch containing the fix")
    base_branch: Optional[str] = Field(default=None, description="Base branch PR targets")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp when PR was created or reconciled")
    message: Optional[str] = Field(default=None, description="Informational summary message")
    error_details: Optional[str] = Field(default=None, description="Safe error details on failure (no secrets)")


