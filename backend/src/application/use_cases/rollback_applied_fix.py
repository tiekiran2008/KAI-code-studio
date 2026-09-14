"""
Rollback Applied Fix Suggestion Use Case
========================================
Reverts an applied code fix on the repository filesystem back to its original
state using AtomicFilePatcher, enforcing strict repository and review ownership,
path sandboxing, and audit logging.
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


class RollbackAppliedFixUseCase:
    """Use case for reverting an applied fix from a local workspace file."""

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
        """Resolve trusted local repository workspace path."""
        if self.workspace_root_resolver:
            resolved = self.workspace_root_resolver(user_id, repository_id)
            if resolved:
                return resolved

        env_ws = os.getenv("WORKSPACE_ROOT")
        if env_ws and os.path.isdir(env_ws):
            return env_ws

        return os.getcwd()

    async def execute(
        self,
        review_id: str,
        finding_index: int,
        user_id: str,
        workspace_root_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rollback an applied fix suggestion from the workspace file.

        Parameters
        ----------
        review_id : str
            ID of the code review.
        finding_index : int
            Index of the finding in findings_json.
        user_id : str
            Authenticated user ID.
        workspace_root_override : Optional[str]
            Optional workspace root path.

        Returns
        -------
        Dict[str, Any]
            Updated fix_suggestion dict and rollback metadata.
        """
        if finding_index < 0:
            raise WorkflowExecutionError(f"finding_index must be >= 0, got {finding_index}")

        lock_key = f"{review_id}:{finding_index}"
        lock = await self._get_lock(lock_key)

        async with lock:
            # 1. Load latest review with ownership check
            review = self.review_service.get_review(review_id, user_id=user_id)
            if not review:
                raise ResourceNotFoundError("Review not found or access denied")

            # 2. Check repository ownership
            repo = self.repository_service.get_repository(user_id=user_id, repo_id=review.repository_id)
            if not repo:
                raise ResourceNotFoundError("Repository not found or access denied")

            # 3. Check finding index range
            findings = list(review.findings_json or [])
            if finding_index >= len(findings):
                raise WorkflowExecutionError(
                    f"finding_index {finding_index} out of range (review has {len(findings)} findings)"
                )

            finding_dict = findings[finding_index]
            fix_dict = finding_dict.get("fix_suggestion")
            if not fix_dict:
                raise WorkflowExecutionError("No fix suggestion exists for this finding")

            # 4. Check that fix is actually applied
            current_app_status = fix_dict.get("application_status")
            if current_app_status != FixApplicationStatus.APPLIED.value:
                # If already rolled back, return idempotent response
                if current_app_status == FixApplicationStatus.ROLLED_BACK.value:
                    return {"fix_suggestion": fix_dict, "idempotent": True, "rolled_back": True}
                raise WorkflowExecutionError(
                    f"Cannot rollback fix with status '{current_app_status}' (must be 'applied')"
                )

            # 5. Resolve workspace root
            workspace_root = workspace_root_override or self._resolve_workspace_root(
                user_id, review.repository_id
            )

            # 6. Construct inverse patch: proposed_code -> original_code
            file_path = fix_dict.get("file_path", "")
            original_code = fix_dict.get("original_code", "")
            proposed_code = fix_dict.get("proposed_code", "")
            expected_hash = fix_dict.get("new_hash")

            rollback_patch = PatchRequest(
                file_path=file_path,
                expected_original=proposed_code,
                proposed_replacement=original_code,
                expected_hash=expected_hash,
            )

            # 7. Execute atomic rollback
            try:
                patch_result = self.atomic_patcher.apply_patch(
                    workspace_root=workspace_root,
                    request=rollback_patch,
                )
            except StaleSourceError as exc:
                raise WorkflowExecutionError(f"Stale source detected during rollback: {exc}")
            except AmbiguousMatchError as exc:
                raise WorkflowExecutionError(f"Ambiguous match during rollback: {exc}")
            except (UnsafePathError, SymlinkEscapeError) as exc:
                raise WorkflowExecutionError(f"Sandbox violation during rollback: {exc}")
            except Exception as exc:
                raise WorkflowExecutionError(f"Rollback execution failed: {exc}")

            # 8. Persist rolled_back state in review DB
            updated_fix = self.review_service.rollback_finding_fix(
                review_id=review_id,
                finding_index=finding_index,
                user_id=user_id,
            )

            logger.info(
                "fix_rolled_back_successfully",
                review_id=review_id,
                finding_index=finding_index,
                file_path=file_path,
                user_id=user_id,
            )

            return {
                "fix_suggestion": updated_fix,
                "patch_result": {
                    "file_path": patch_result.file_path,
                    "success": patch_result.success,
                    "changed": patch_result.changed,
                    "message": "Fix successfully rolled back to original source code",
                },
                "rolled_back": True,
            }
