"""
Apply Fix Suggestion Use Case
==============================
Orchestrates the safe, authorized, and concurrent-safe application of an
accepted FixSuggestion to a target file in the repository workspace.

Key Invariants:
1. Strict user ownership of BOTH Review and Repository.
2. Review must be in COMPLETED status.
3. Fix suggestion MUST have user_decision == ACCEPTED.
4. Validation status must NOT be INVALID.
5. In-process mutex locking per (review_id, finding_index) to prevent race conditions.
6. Re-reads latest DB state inside the lock for idempotency.
7. Uses AtomicFilePatcher (Phase 11.3B-1) for path sandboxing, stale-source protection, and atomic write.
8. Implements compensating rollback if database update fails after filesystem patch.
9. ZERO LLM calls, ZERO arbitrary code execution, ZERO general tool registration.
"""
import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from src.core.logger import logger
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError
from src.domain.entities.code_review import ReviewStatusEnum
from src.domain.entities.fix_suggestion import (
    FixUserDecision,
    FixValidationStatus,
    FixApplicationStatus,
)
from src.domain.entities.patch import (
    PatchRequest,
    PatchResult,
    PatchError,
    StaleSourceError,
    AmbiguousMatchError,
    UnsafePathError,
    SymlinkEscapeError,
    TargetFileNotFoundError,
    EncodingError,
    AtomicWriteError,
    PatchVerificationError,
    RollbackError,
)
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService
from src.application.services.atomic_patcher import AtomicFilePatcher


class ApplyFixSuggestionUseCase:
    """Use case for applying an accepted FixSuggestion to a local workspace file."""

    _global_locks: Dict[str, asyncio.Lock] = {}
    _global_lock_guard: Optional[asyncio.Lock] = None

    @classmethod
    def _get_guard(cls) -> asyncio.Lock:
        if cls._global_lock_guard is None:
            cls._global_lock_guard = asyncio.Lock()
        return cls._global_lock_guard

    def __init__(
        self,
        review_service: CodeReviewService,
        repository_service: RepositoryService,
        atomic_patcher: Optional[AtomicFilePatcher] = None,
        workspace_root_resolver: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self.review_service = review_service
        self.repository_service = repository_service
        self.atomic_patcher = atomic_patcher or AtomicFilePatcher()
        self.workspace_root_resolver = workspace_root_resolver

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Fetch or create a per-fix mutex lock in a concurrency-safe manner."""
        guard = self._get_guard()
        async with guard:
            if key not in self._global_locks:
                self._global_locks[key] = asyncio.Lock()
            return self._global_locks[key]

    def _resolve_workspace_root(self, user_id: str, repository_id: str) -> str:
        """Resolve trusted local repository workspace path from configuration or service."""
        if self.workspace_root_resolver:
            resolved = self.workspace_root_resolver(user_id, repository_id)
            if resolved:
                return resolved

        # Default fallback to environment or relative workspace directory
        env_ws = os.getenv("WORKSPACE_ROOT")
        if env_ws and os.path.isdir(env_ws):
            return env_ws

        # Use current working directory as default safe workspace
        return os.getcwd()

    async def execute(
        self,
        review_id: str,
        finding_index: int,
        user_id: str,
        workspace_root_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply an accepted fix suggestion to the workspace file.

        Parameters
        ----------
        review_id : str
            ID of the code review.
        finding_index : int
            Index of the finding in the review's findings_json.
        user_id : str
            Authenticated user ID (must own review and repository).
        workspace_root_override : Optional[str]
            Optional workspace root path (for testing or explicit binding).

        Returns
        -------
        Dict[str, Any]
            Dictionary containing 'fix_suggestion' and 'idempotent' boolean.

        Raises
        ------
        ResourceNotFoundError
            If review or repository is not found or not owned by user.
        WorkflowExecutionError
            If validation, status, decision, or patch fails.
        """
        if finding_index < 0:
            raise WorkflowExecutionError(f"finding_index must be >= 0, got {finding_index}")

        lock_key = f"{review_id}:{finding_index}"
        lock = await self._get_lock(lock_key)

        async with lock:
            # 1. Load latest review inside lock with ownership enforcement
            review = self.review_service.get_review(review_id, user_id=user_id)
            if not review:
                raise ResourceNotFoundError("Review not found or access denied")

            # 2. Check review status
            if review.status != ReviewStatusEnum.COMPLETED.value:
                raise WorkflowExecutionError(
                    f"Fix application requires a completed review (current status: '{review.status}')"
                )

            # 3. Check repository ownership
            repo = self.repository_service.get_repository(user_id=user_id, repo_id=review.repository_id)
            if not repo:
                raise ResourceNotFoundError("Repository not found or access denied")

            # 4. Check finding index range
            findings = list(review.findings_json or [])
            if finding_index >= len(findings):
                raise WorkflowExecutionError(
                    f"finding_index {finding_index} out of range (review has {len(findings)} findings)"
                )

            finding_dict = findings[finding_index]
            fix_dict = finding_dict.get("fix_suggestion")
            if not fix_dict:
                raise WorkflowExecutionError("No fix suggestion exists for this finding")

            # 5. Check user decision — MUST be accepted
            user_decision = fix_dict.get("user_decision")
            if user_decision != FixUserDecision.ACCEPTED.value:
                raise WorkflowExecutionError(
                    f"Fix suggestion must be accepted before applying (current decision: '{user_decision}')"
                )

            # 6. Check validation status — must NOT be invalid
            validation_status = fix_dict.get("validation_status")
            if validation_status == FixValidationStatus.INVALID.value:
                raise WorkflowExecutionError(
                    "Cannot apply fix suggestion with invalid syntax validation"
                )

            # 7. Idempotency check: if already APPLIED, return immediately
            if fix_dict.get("application_status") == FixApplicationStatus.APPLIED.value:
                logger.info(
                    "fix_application_already_applied",
                    review_id=review_id,
                    finding_index=finding_index,
                )
                return {"fix_suggestion": fix_dict, "idempotent": True}

            # 8. Resolve trusted workspace root
            workspace_root = workspace_root_override or self._resolve_workspace_root(
                user_id, review.repository_id
            )

            # 9. Construct deterministic PatchRequest
            file_path = fix_dict.get("file_path", "")
            original_code = fix_dict.get("original_code", "")
            proposed_code = fix_dict.get("proposed_code", "")
            expected_hash = fix_dict.get("previous_hash")

            patch_req = PatchRequest(
                file_path=file_path,
                expected_original=original_code,
                proposed_replacement=proposed_code,
                expected_hash=expected_hash,
            )

            # 10. Execute atomic patch
            try:
                patch_result = self.atomic_patcher.apply_patch(
                    workspace_root=workspace_root,
                    request=patch_req,
                )
            except StaleSourceError as exc:
                self.review_service.update_finding_application_status(
                    review_id=review_id,
                    finding_index=finding_index,
                    application_status=FixApplicationStatus.STALE,
                    application_error=str(exc),
                    user_id=user_id,
                )
                raise WorkflowExecutionError(f"Stale source detected: {exc}")
            except AmbiguousMatchError as exc:
                self.review_service.update_finding_application_status(
                    review_id=review_id,
                    finding_index=finding_index,
                    application_status=FixApplicationStatus.APPLY_FAILED,
                    application_error=str(exc),
                    user_id=user_id,
                )
                raise WorkflowExecutionError(f"Ambiguous match: {exc}")
            except (UnsafePathError, SymlinkEscapeError) as exc:
                self.review_service.update_finding_application_status(
                    review_id=review_id,
                    finding_index=finding_index,
                    application_status=FixApplicationStatus.APPLY_FAILED,
                    application_error="Path violates repository sandbox boundary",
                    user_id=user_id,
                )
                raise WorkflowExecutionError(f"Sandbox violation: {exc}")
            except (AtomicWriteError, PatchVerificationError, TargetFileNotFoundError, EncodingError, PatchError) as exc:
                self.review_service.update_finding_application_status(
                    review_id=review_id,
                    finding_index=finding_index,
                    application_status=FixApplicationStatus.APPLY_FAILED,
                    application_error=str(exc),
                    user_id=user_id,
                )
                raise WorkflowExecutionError(f"Patch execution failed: {exc}")
            except Exception as exc:
                self.review_service.update_finding_application_status(
                    review_id=review_id,
                    finding_index=finding_index,
                    application_status=FixApplicationStatus.APPLY_FAILED,
                    application_error="Unexpected patch error",
                    user_id=user_id,
                )
                raise WorkflowExecutionError(f"Unexpected patch failure: {exc}")

            # 11. Persist APPLIED status to database
            applied_at = datetime.now(timezone.utc).isoformat()

            try:
                updated_fix = self.review_service.update_finding_application_status(
                    review_id=review_id,
                    finding_index=finding_index,
                    application_status=FixApplicationStatus.APPLIED,
                    applied_at=applied_at,
                    previous_hash=patch_result.previous_hash,
                    new_hash=patch_result.new_hash,
                    application_error=None,
                    user_id=user_id,
                )
            except Exception as db_exc:
                logger.error(
                    "patch_db_update_failed_initiating_compensation",
                    review_id=review_id,
                    finding_index=finding_index,
                    error=str(db_exc),
                )
                # Compensating rollback: restore original file content on disk
                try:
                    rollback_req = PatchRequest(
                        file_path=file_path,
                        expected_original=proposed_code,
                        proposed_replacement=original_code,
                    )
                    self.atomic_patcher.apply_patch(workspace_root, rollback_req)
                    logger.info("compensating_rollback_succeeded", review_id=review_id, file_path=file_path)
                except Exception as rb_exc:
                    logger.critical(
                        "compensating_rollback_failed",
                        review_id=review_id,
                        finding_index=finding_index,
                        error=str(rb_exc),
                    )
                raise WorkflowExecutionError(
                    f"Failed to persist applied fix state to database; compensating rollback executed: {db_exc}"
                )

            logger.info(
                "fix_suggestion_applied_successfully",
                review_id=review_id,
                finding_index=finding_index,
                file_path=file_path,
                previous_hash=patch_result.previous_hash[:8],
                new_hash=patch_result.new_hash[:8],
            )

            return {"fix_suggestion": updated_fix, "idempotent": False}
