"""
Verify Applied Fix Use Case (Tier-1)
====================================
Orchestrates safe, in-memory Tier-1 static and syntax verification of a
previously applied fix on the current workspace target file.

Key Invariants:
1. Strict user ownership of BOTH Review and Repository.
2. Review must be in COMPLETED status.
3. Fix suggestion MUST have application_status == APPLIED.
4. Reads the target file via PathSandboxService (READ-ONLY).
5. Detects post-apply source file modifications (SOURCE_CHANGED).
6. Runs in-memory deterministic syntax & static checks (StaticVerificationEngine).
7. Persists verification result metadata into findings_json (0 DB migration).
8. ZERO LLM calls, ZERO subprocess / shell execution, ZERO repository code execution.
"""
import asyncio
import hashlib
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from src.core.logger import logger
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError
from src.domain.entities.code_review import ReviewStatusEnum
from src.domain.entities.fix_suggestion import FixApplicationStatus, FixUserDecision
from src.domain.entities.verification import (
    VerificationStatus,
    CheckStatus,
    VerificationCheck,
    StaticVerificationResult,
)
from src.infrastructure.filesystem.path_sandbox import PathSandboxService
from src.infrastructure.analysis.static_verification_engine import StaticVerificationEngine
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService


class VerifyAppliedFixUseCase:
    """Use case for executing in-memory static verification of an applied fix."""

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
        verification_engine: Optional[StaticVerificationEngine] = None,
        path_sandbox: Optional[PathSandboxService] = None,
        workspace_root_resolver: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self.review_service = review_service
        self.repository_service = repository_service
        self.engine = verification_engine or StaticVerificationEngine()
        self.sandbox = path_sandbox or PathSandboxService()
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
        """Verify an applied fix suggestion using in-memory Tier-1 checks.

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
            Dictionary containing 'verification' (StaticVerificationResult) and 'fix_suggestion'.

        Raises
        ------
        ResourceNotFoundError
            If review or repository is not found or not owned by user.
        WorkflowExecutionError
            If review status, finding index, application status, or path resolution fails.
        """
        if finding_index < 0:
            raise WorkflowExecutionError(f"finding_index must be >= 0, got {finding_index}")

        lock_key = f"verify:{review_id}:{finding_index}"
        lock = await self._get_lock(lock_key)

        async with lock:
            # 1. Ownership enforcement: review ownership
            review = self.review_service.get_review(review_id, user_id=user_id)
            if not review:
                raise ResourceNotFoundError("Review not found or access denied")

            # 2. Status enforcement
            if review.status != ReviewStatusEnum.COMPLETED.value:
                raise WorkflowExecutionError(
                    f"Verification requires a completed review (current status: '{review.status}')"
                )

            # 3. Ownership enforcement: repository ownership
            repo = self.repository_service.get_repository(
                user_id=user_id, repo_id=review.repository_id
            )
            if not repo:
                raise ResourceNotFoundError("Repository not found or access denied")

            # 4. Finding range validation
            findings = list(review.findings_json or [])
            if finding_index >= len(findings):
                raise WorkflowExecutionError(
                    f"finding_index {finding_index} out of range (review has {len(findings)} findings)"
                )

            finding_dict = findings[finding_index]
            fix_dict = finding_dict.get("fix_suggestion")
            if not fix_dict:
                raise WorkflowExecutionError("No fix suggestion exists for this finding")

            # 5. Eligibility check: application_status MUST be APPLIED
            app_status = fix_dict.get("application_status")
            if app_status != FixApplicationStatus.APPLIED.value:
                raise WorkflowExecutionError(
                    f"Fix suggestion must be applied before running verification (current status: '{app_status}')"
                )

            user_dec = fix_dict.get("user_decision")
            if user_dec == FixUserDecision.REJECTED.value:
                raise WorkflowExecutionError(
                    "Cannot verify a rejected fix suggestion"
                )

            # 6. Resolve trusted workspace root & target path
            workspace_root = workspace_root_override or self._resolve_workspace_root(
                user_id, review.repository_id
            )
            file_path = fix_dict.get("file_path", "")

            try:
                target_path = self.sandbox.validate_path(
                    workspace_root=workspace_root,
                    relative_path=file_path,
                    must_be_file=True,
                )
            except Exception as exc:
                raise WorkflowExecutionError(f"Target path validation failed: {exc}")

            if not target_path.exists() or not target_path.is_file():
                raise WorkflowExecutionError(f"Target file does not exist on disk: '{file_path}'")

            # 7. Safe read-only file read
            try:
                current_bytes = target_path.read_bytes()
                current_source = current_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise WorkflowExecutionError(f"File '{file_path}' is not valid UTF-8: {exc}")
            except Exception as exc:
                raise WorkflowExecutionError(f"Failed reading file '{file_path}': {exc}")

            current_hash = hashlib.sha256(current_bytes).hexdigest()
            applied_new_hash = fix_dict.get("new_hash")

            # 8. Post-apply modification check (Source Changed Detection)
            if applied_new_hash and applied_new_hash.strip():
                if current_hash.lower() != applied_new_hash.strip().lower():
                    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    changed_result = StaticVerificationResult(
                        status=VerificationStatus.SOURCE_CHANGED,
                        language=fix_dict.get("language") or self.engine.detect_language(file_path),
                        verified_at=now_iso,
                        verified_hash=current_hash,
                        duration_ms=0,
                        checks=[
                            VerificationCheck(
                                name="source_hash_integrity",
                                status=CheckStatus.FAILED,
                                message="Source file was modified after fix was applied; verification aborted to prevent false claims",
                            )
                        ],
                        errors=["Source file hash mismatch since patch application"],
                        warnings=["File content changed post-apply"],
                        message="Verification aborted: target file was modified after fix application",
                    )
                    updated_fix = self.review_service.update_finding_verification_result(
                        review_id=review_id,
                        finding_index=finding_index,
                        verification_result=changed_result,
                        user_id=user_id,
                    )
                    return {
                        "verification": changed_result,
                        "fix_suggestion": updated_fix,
                    }

            # 9. Execute Tier-1 in-memory verification engine
            hint_lang = fix_dict.get("language")
            verification_result = self.engine.verify_source(
                source_text=current_source,
                file_path=file_path,
                hint_language=hint_lang,
                expected_hash=applied_new_hash,
            )

            # 10. Persist verification result into review findings_json
            updated_fix = self.review_service.update_finding_verification_result(
                review_id=review_id,
                finding_index=finding_index,
                verification_result=verification_result,
                user_id=user_id,
            )

            logger.info(
                "applied_fix_verification_completed",
                review_id=review_id,
                finding_index=finding_index,
                status=verification_result.status.value,
                duration_ms=verification_result.duration_ms,
            )

            return {
                "verification": verification_result,
                "fix_suggestion": updated_fix,
            }
