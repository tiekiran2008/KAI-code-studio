"""
Verify Applied Fix Tests Use Case (Tier-2)
==========================================
Orchestrates safe, containerized Tier-2 isolated test verification of a
previously applied fix on the repository workspace.

Key Invariants:
1. Strict user ownership of BOTH Review and Repository.
2. Review must be in COMPLETED status.
3. Fix suggestion MUST have application_status == APPLIED.
4. Tier-1 Static Verification MUST have status == PASSED.
5. Current workspace target file must exist and match applied new_hash (SOURCE_CHANGED detection).
6. Execution parameters generated server-side from allowlists (Python + pytest only).
7. Ephemeral workspace copy created; original repository on host is never mutated.
8. Zero host fallback: if Docker is unavailable, returns SANDBOX_UNAVAILABLE.
9. Persists Tier-2 result into findings_json (0 DB schema migrations).
10. ZERO LLM calls, ZERO host process / subprocess execution.
"""
import asyncio
import hashlib
import os
import time
from typing import Dict, Any, Optional, Callable

from src.core.logger import logger
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError
from src.domain.entities.code_review import ReviewStatusEnum
from src.domain.entities.fix_suggestion import FixApplicationStatus, FixUserDecision
from src.domain.entities.verification import VerificationStatus
from src.domain.entities.sandbox import (
    SandboxExecutionRequest,
    SandboxVerificationResult,
    SandboxVerificationStatusEnum,
)
from src.infrastructure.filesystem.path_sandbox import PathSandboxService
from src.infrastructure.sandbox.sandbox_engine import SandboxExecutionEngine
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService


class VerifyAppliedFixTestsUseCase:
    """Use case for executing container-isolated Tier-2 test verification of an applied fix."""

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
        sandbox_engine: Optional[SandboxExecutionEngine] = None,
        path_sandbox: Optional[PathSandboxService] = None,
        workspace_root_resolver: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self.review_service = review_service
        self.repository_service = repository_service
        self.sandbox_engine = sandbox_engine or SandboxExecutionEngine()
        self.path_sandbox = path_sandbox or PathSandboxService()
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
        """Execute isolated container tests for an applied fix suggestion.

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
            Dictionary containing 'verification' (SandboxVerificationResult) and 'fix_suggestion'.

        Raises
        ------
        ResourceNotFoundError
            If review or repository is not found or not owned by user.
        WorkflowExecutionError
            If review status, finding index, eligibility, or source consistency fails.
        """
        if finding_index < 0:
            raise WorkflowExecutionError(f"finding_index must be >= 0, got {finding_index}")

        lock_key = f"verify_tests:{review_id}:{finding_index}"
        lock = await self._get_lock(lock_key)

        async with lock:
            # 1. Ownership enforcement: review ownership
            review = self.review_service.get_review(review_id, user_id=user_id)
            if not review:
                raise ResourceNotFoundError("Review not found or access denied")

            # 2. Status enforcement: review must be completed
            if review.status != ReviewStatusEnum.COMPLETED.value:
                raise WorkflowExecutionError(
                    f"Tier-2 verification requires a completed review (current status: '{review.status}')"
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
                    f"Fix suggestion must be applied before running isolated tests (current status: '{app_status}')"
                )

            user_dec = fix_dict.get("user_decision")
            if user_dec == FixUserDecision.REJECTED.value:
                raise WorkflowExecutionError("Cannot run isolated tests on a rejected fix suggestion")

            # 6. Tier-1 Prerequisite Check: Static Verification must be PASSED
            static_ver = fix_dict.get("static_verification")
            if not static_ver:
                raise WorkflowExecutionError(
                    "Tier-1 static verification must pass before running isolated repository tests"
                )

            static_status = static_ver.get("status") if isinstance(static_ver, dict) else getattr(static_ver, "status", None)
            if static_status != VerificationStatus.PASSED.value and static_status != VerificationStatus.PASSED:
                raise WorkflowExecutionError(
                    f"Tier-1 static verification must be 'passed' to run isolated tests (current status: '{static_status}')"
                )

            # 7. Resolve workspace root & target path
            workspace_root = workspace_root_override or self._resolve_workspace_root(
                user_id, review.repository_id
            )
            file_path = fix_dict.get("file_path", "")

            try:
                target_path = self.path_sandbox.validate_path(
                    workspace_root=workspace_root,
                    relative_path=file_path,
                    must_be_file=True,
                )
            except Exception as exc:
                raise WorkflowExecutionError(f"Target path validation failed: {exc}")

            if not target_path.exists() or not target_path.is_file():
                raise WorkflowExecutionError(f"Target file does not exist on disk: '{file_path}'")

            # 8. Source Hash Consistency Check (detects post-apply modification)
            try:
                current_bytes = target_path.read_bytes()
            except Exception as exc:
                raise WorkflowExecutionError(f"Failed reading target file '{file_path}': {exc}")

            current_hash = hashlib.sha256(current_bytes).hexdigest()
            applied_new_hash = fix_dict.get("new_hash")

            if applied_new_hash and applied_new_hash.strip():
                if current_hash.lower() != applied_new_hash.strip().lower():
                    raise WorkflowExecutionError(
                        "Source file was modified after fix was applied. Cannot run isolated tests on stale source."
                    )

            # 9. Language & Framework Stack Detection
            repo_stack = repo.detected_stack if hasattr(repo, "detected_stack") and repo.detected_stack else {}
            detected_lang = None
            if isinstance(repo_stack, dict):
                detected_lang = repo_stack.get("language")
            elif hasattr(repo_stack, "language"):
                detected_lang = repo_stack.language

            # Infer from file extension if repo detected_stack is generic
            if file_path.endswith(".py") or (detected_lang and "python" in detected_lang.lower()):
                language = "Python"
                framework = "pytest"
            else:
                language = detected_lang or "unsupported"
                framework = "unsupported"

            # 10. Construct trusted execution request
            exec_request = SandboxExecutionRequest(
                workspace_root=workspace_root,
                verification_type="isolated_tests",
                language=language,
                framework=framework,
                timeout_seconds=30,
                relative_target_path=None,
                repository_id=review.repository_id,
                review_id=review_id,
                finding_index=finding_index,
            )

            # 11. Execute in container sandbox
            verification_result = await self.sandbox_engine.execute_verification(exec_request)
            verification_result.verified_hash = current_hash

            # 12. Persist Tier-2 result in review findings_json
            updated_fix = self.review_service.update_finding_test_verification_result(
                review_id=review_id,
                finding_index=finding_index,
                verification_result=verification_result,
                user_id=user_id,
            )

            logger.info(
                "isolated_test_verification_completed",
                review_id=review_id,
                finding_index=finding_index,
                status=verification_result.status.value,
                duration_ms=verification_result.duration_ms,
                tests_passed=verification_result.tests_passed,
                tests_failed=verification_result.tests_failed,
            )

            return {
                "verification": verification_result,
                "fix_suggestion": updated_fix,
            }
