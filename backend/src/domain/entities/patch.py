"""
Patch Domain Entities and Exceptions
====================================
Strongly typed domain models and typed exceptions for safe atomic file patching.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Typed Exceptions
# =============================================================================

class PatchError(Exception):
    """Base exception for all patch operations."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UnsafePathError(PatchError):
    """Raised when a target file path attempts to escape the repository sandbox."""
    pass


class SymlinkEscapeError(PatchError):
    """Raised when a symlink resolves to a location outside the repository sandbox."""
    pass


class TargetFileNotFoundError(PatchError):
    """Raised when the target file to be patched does not exist."""
    pass


class StaleSourceError(PatchError):
    """Raised when the expected original snippet does not exist in the target file."""
    pass


class AmbiguousMatchError(PatchError):
    """Raised when the expected original snippet occurs more than once in the target file."""
    pass


class EncodingError(PatchError):
    """Raised when the target file cannot be decoded or encoded safely."""
    pass


class AtomicWriteError(PatchError):
    """Raised when the atomic file replacement fails."""
    pass


class PatchVerificationError(PatchError):
    """Raised when post-write content verification fails."""
    pass


class RollbackError(PatchError):
    """Raised when rollback of a failed patch operation fails."""
    pass


# =============================================================================
# Domain Models
# =============================================================================

class PatchRequest(BaseModel):
    """Request payload for an atomic snippet replacement operation."""
    file_path: str = Field(..., min_length=1, description="Relative path to target file within repository")
    expected_original: str = Field(..., min_length=1, description="Expected original code snippet to be replaced")
    proposed_replacement: str = Field(..., min_length=1, description="Proposed fixed code snippet to insert")
    expected_hash: Optional[str] = Field(default=None, description="Optional SHA-256 hash of original file content")

    @field_validator("file_path", "expected_original", "proposed_replacement")
    @classmethod
    def _validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v


class PatchResult(BaseModel):
    """Result of an atomic patch operation."""
    file_path: str = Field(..., description="Relative path to patched file")
    success: bool = Field(..., description="Whether the patch succeeded")
    changed: bool = Field(default=True, description="Whether the file content actually changed")
    previous_hash: str = Field(default="", description="SHA-256 hash of file before patch")
    new_hash: str = Field(default="", description="SHA-256 hash of file after patch")
    bytes_written: int = Field(default=0, ge=0, description="Total bytes written to disk")
    rollback_performed: bool = Field(default=False, description="Whether a rollback was executed due to failure")
    message: str = Field(default="", description="Human-readable status or error message")
