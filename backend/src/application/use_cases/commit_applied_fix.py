"""
Commit Applied Fix Use Case
===========================
Orchestrates the safe, authorized, and isolated local Git committing of an
applied fix suggestion to a dedicated AI fix branch.

Key Invariants:
1. Strict user ownership of BOTH Review and Repository.
2. Review must be in COMPLETED status.
3. Fix suggestion MUST have application_status == APPLIED.
4. Tier-1 Static Verification MUST have status == PASSED.
5. Current workspace target file must exist and match applied new_hash (STALE_SOURCE protection).
6. Uses GitWorkingTreeManager with temporary index isolation (zero mutation of user's active branch or user-staged files).
7. In-process mutex locking per repository_id to serialize concurrent Git operations.
8. Idempotent: repeated calls for an already committed fix return existing commit metadata without duplicate commit objects.
9. ZERO push, ZERO GitHub API calls, ZERO LLM calls.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from src.core.logger import logger
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError
from src.domain.entities.code_review import ReviewStatusEnum
from src.domain.entities.fix_suggestion import FixApplicationStatus, FixUserDecision
from src.domain.entities.verification import VerificationStatus
from src.domain.entities.git import (
    GitCommitResult,
    GitCommitStatusEnum,
)
from src.infrastructure.filesystem.path_sandbox import PathSandboxService
from src.infrastructure.git.working_tree_manager import GitWorkingTreeManager
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService


class CommitAppliedFixUseCase:
    """Use case for creating an isolated local Git commit on a dedicated branch."""

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
        working_tree_manager: Optional[GitWorkingTreeManager] = None,
        path_sandbox: Optional[PathSandboxService] = None,
        workspace_root_resolver: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self.review_service = review_service
        self.repository_service = repository_service
        self.working_tree_manager = working_tree_manager or GitWorkingTreeManager()
        self.path_sandbox = path_sandbox or PathSandboxService()
        self.workspace_root_resolver = workspace_root_resolver

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """Fetch or create a per-repository mutex lock in a concurrency-safe manner."""
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
        custom_branch_name: Optional[str] = None,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
        workspace_root_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute isolated local Git commit for an applied fix suggestion.

        Parameters
        ----------
        review_id : str
            ID of the code review.
        finding_index : int
            Index of the finding in the review's findings_json.
        user_id : str
            Authenticated user ID (must own review and repository).
        custom_branch_name : Optional[str]
            Optional custom branch name (will be validated for safety).
        author_name : Optional[str]
            Optional Git commit author name.
        author_email : Optional[str]
            Optional Git commit author email.
        workspace_root_override : Optional[str]
            Optional workspace root path (for testing or explicit binding).

        Returns
        -------
        Dict[str, Any]
            Dictionary containing 'git_commit' (GitCommitResult) and 'fix_suggestion'.
        """
        if finding_index < 0:
            raise WorkflowExecutionError(f"finding_index must be >= 0, got {finding_index}")

        # 1. Ownership enforcement: review ownership
        review = self.review_service.get_review(review_id, user_id=user_id)
        if not review:
            raise ResourceNotFoundError("Review not found or access denied")

        # Serialize Git operations per repository to prevent index lock conflicts
        lock_key = f"git:{review.repository_id}"
        lock = await self._get_lock(lock_key)

        async with lock:
            # Re-read review inside lock
            review = self.review_service.get_review(review_id, user_id=user_id)
            if not review:
                raise ResourceNotFoundError("Review not found or access denied")

            # 2. Status enforcement: review must be completed
            if review.status != ReviewStatusEnum.COMPLETED.value:
                raise WorkflowExecutionError(
                    f"Git commit requires a completed review (current status: '{review.status}')"
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
                    f"Fix suggestion must be applied before committing (current status: '{app_status}')"
                )

            user_dec = fix_dict.get("user_decision")
            if user_dec == FixUserDecision.REJECTED.value:
                raise WorkflowExecutionError("Cannot commit a rejected fix suggestion")

            # 6. Tier-1 Prerequisite Check: Static Verification must be PASSED
            static_ver = fix_dict.get("static_verification")
            if not static_ver:
                raise WorkflowExecutionError(
                    "Tier-1 static verification must pass before committing fix to Git"
                )

            static_status = (
                static_ver.get("status")
                if isinstance(static_ver, dict)
                else getattr(static_ver, "status", None)
            )
            if static_status != VerificationStatus.PASSED.value and static_status != VerificationStatus.PASSED:
                raise WorkflowExecutionError(
                    f"Tier-1 static verification must be 'passed' to commit fix (current status: '{static_status}')"
                )

            # 7. Idempotency Check: if already committed, return existing commit
            existing_commit = fix_dict.get("git_commit")
            if existing_commit:
                existing_status = (
                    existing_commit.get("status")
                    if isinstance(existing_commit, dict)
                    else getattr(existing_commit, "status", None)
                )
                if existing_status in (GitCommitStatusEnum.COMMITTED.value, GitCommitStatusEnum.ALREADY_COMMITTED.value):
                    parsed_existing = (
                        GitCommitResult(**existing_commit)
                        if isinstance(existing_commit, dict)
                        else existing_commit
                    )
                    return {
                        "git_commit": parsed_existing,
                        "fix_suggestion": fix_dict,
                    }

            # 8. Resolve workspace root & target path
            workspace_root_str = workspace_root_override or self._resolve_workspace_root(
                user_id, review.repository_id
            )
            workspace_root = Path(workspace_root_str).resolve()
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

            # 9. Source Hash Consistency Check (detects post-apply modification)
            try:
                current_bytes = target_path.read_bytes()
            except Exception as exc:
                raise WorkflowExecutionError(f"Failed reading target file '{file_path}': {exc}")

            current_hash = hashlib.sha256(current_bytes).hexdigest()
            applied_new_hash = fix_dict.get("new_hash")

            if applied_new_hash and applied_new_hash.strip():
                if current_hash.lower() != applied_new_hash.strip().lower():
                    raise WorkflowExecutionError(
                        "Source file was modified after fix was applied. Cannot commit stale source."
                    )

            # 10. Execute isolated commit on dedicated branch
            commit_result = self.working_tree_manager.create_isolated_fix_commit(
                workspace_root=workspace_root,
                relative_target_path=file_path,
                review_id=review_id,
                finding_index=finding_index,
                finding_issue=finding_dict.get("issue"),
                custom_branch_name=custom_branch_name,
                author_name=author_name,
                author_email=author_email,
            )

            # 11. Persist Git commit metadata in review findings_json
            updated_fix = self.review_service.update_finding_git_commit_result(
                review_id=review_id,
                finding_index=finding_index,
                git_commit_result=commit_result,
                user_id=user_id,
            )

            logger.info(
                "git_fix_commit_use_case_completed",
                review_id=review_id,
                finding_index=finding_index,
                status=commit_result.status.value,
                branch=commit_result.branch_name,
                commit_sha=commit_result.commit_sha,
            )

            return {
                "git_commit": commit_result,
                "fix_suggestion": updated_fix,
            }
