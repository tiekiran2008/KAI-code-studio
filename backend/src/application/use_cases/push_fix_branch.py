"""
Push Fix Branch Use Case
=========================
Executes a safe, non-destructive Git push of a dedicated AI fix branch
to the trusted configured remote repository (e.g. 'origin').

Enforces:
- Review and repository ownership verification
- Completed review status
- Fix suggestion exists, accepted, and applied
- Local Git commit prerequisite (verified commit SHA and branch name)
- Exact ref push with structured argv (zero shell, zero force flags)
- Trusted remote validation against owned repository metadata
- Per-repository asyncio mutex lock
- Idempotency (already pushed returns existing result)
- Persistence in review findings JSON metadata
- Zero PR creation, zero LLM calls, zero push of user active branch
"""
import asyncio
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from src.core.errors import ResourceNotFoundError, WorkflowExecutionError
from src.core.logger import logger
from src.domain.entities.git import GitPushResult, GitPushStatusEnum
from src.domain.entities.fix_suggestion import FixApplicationStatus, FixUserDecision
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService
from src.infrastructure.git.working_tree_manager import GitWorkingTreeManager


_REPO_PUSH_LOCKS: Dict[str, asyncio.Lock] = {}


def _get_repo_push_lock(repo_id: str) -> asyncio.Lock:
    """Return an asyncio.Lock per repository to serialize Git push operations."""
    if repo_id not in _REPO_PUSH_LOCKS:
        _REPO_PUSH_LOCKS[repo_id] = asyncio.Lock()
    return _REPO_PUSH_LOCKS[repo_id]


class PushFixBranchUseCase:
    """Use case for safely pushing a dedicated AI fix branch to a trusted remote."""

    def __init__(
        self,
        review_service: CodeReviewService,
        repository_service: RepositoryService,
        working_tree_manager: Optional[GitWorkingTreeManager] = None,
        workspace_root_resolver: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self.review_service = review_service
        self.repository_service = repository_service
        self.working_tree_manager = working_tree_manager or GitWorkingTreeManager()
        self.workspace_root_resolver = workspace_root_resolver

    def _resolve_workspace_root(self, user_id: str, repository_id: str) -> Path:
        """Resolve workspace root directory for the given user and repository."""
        if self.workspace_root_resolver:
            resolved = self.workspace_root_resolver(user_id, repository_id)
            return Path(resolved)

        workspace_env = os.getenv("WORKSPACE_ROOT")
        if workspace_env:
            return Path(workspace_env)

        return Path.cwd()

    async def execute(
        self,
        review_id: str,
        finding_index: int,
        user_id: str,
        remote_name: str = "origin",
    ) -> Dict[str, Any]:
        """Execute the safe branch push for an eligible fix suggestion.

        Parameters
        ----------
        review_id : str
            ID of the code review.
        finding_index : int
            0-based index of finding in review.findings_json.
        user_id : str
            Authenticated user ID from token.
        remote_name : str
            Trusted remote name (default: 'origin').

        Returns
        -------
        Dict[str, Any]
            {"git_push": GitPushResult, "fix_suggestion": dict}
        """
        # 1. Reject negative index
        if finding_index < 0:
            raise WorkflowExecutionError(
                f"finding_index must be >= 0, got {finding_index}"
            )

        # 2. Review verification & ownership check
        review = self.review_service.get_review(review_id, user_id=user_id)
        if not review:
            raise ResourceNotFoundError("Review not found or access denied")

        if review.status != "completed":
            raise WorkflowExecutionError("Git branch push requires a completed review")

        # 3. Repository verification & ownership check
        repository = self.repository_service.get_repository(
            review.repository_id, user_id=user_id
        )
        if not repository:
            raise ResourceNotFoundError("Repository not found or access denied")

        # 4. Finding range & fix suggestion existence
        findings = list(review.findings_json or [])
        if finding_index >= len(findings):
            raise WorkflowExecutionError(
                f"finding_index {finding_index} out of range (0-{len(findings) - 1})"
            )

        finding = findings[finding_index]
        fix = finding.get("fix_suggestion")
        if not fix:
            raise WorkflowExecutionError("No fix suggestion exists for this finding")

        # 5. Eligibility checks
        app_status = fix.get("application_status")
        if app_status != FixApplicationStatus.APPLIED.value:
            raise WorkflowExecutionError(
                "Fix suggestion must be applied before pushing branch"
            )

        user_dec = fix.get("user_decision")
        if user_dec == FixUserDecision.REJECTED.value:
            raise WorkflowExecutionError("Cannot push a rejected fix suggestion")

        # 6. Local Git Commit Prerequisite
        git_commit_raw = fix.get("git_commit")
        if not git_commit_raw:
            raise WorkflowExecutionError(
                "Fix suggestion must have a local Git commit before pushing"
            )

        commit_status = (
            git_commit_raw.get("status")
            if isinstance(git_commit_raw, dict)
            else getattr(git_commit_raw, "status", None)
        )
        if commit_status not in ("committed", "already_committed"):
            raise WorkflowExecutionError(
                "Local Git commit must be in 'committed' status to push"
            )

        branch_name = (
            git_commit_raw.get("branch_name")
            if isinstance(git_commit_raw, dict)
            else getattr(git_commit_raw, "branch_name", None)
        )
        commit_sha = (
            git_commit_raw.get("commit_sha")
            if isinstance(git_commit_raw, dict)
            else getattr(git_commit_raw, "commit_sha", None)
        )

        if not branch_name or not commit_sha:
            raise WorkflowExecutionError(
                "Local Git commit metadata missing branch_name or commit_sha"
            )

        # 7. Idempotency Check: if already pushed, return existing result
        existing_push = fix.get("git_push")
        if existing_push:
            existing_status = (
                existing_push.get("status")
                if isinstance(existing_push, dict)
                else getattr(existing_push, "status", None)
            )
            if existing_status in (
                GitPushStatusEnum.PUSHED.value,
                GitPushStatusEnum.ALREADY_PUSHED.value,
            ):
                logger.info(
                    "git_push_idempotent_hit",
                    review_id=review_id,
                    finding_index=finding_index,
                    branch_name=branch_name,
                )
                return {
                    "git_push": (
                        GitPushResult(**existing_push)
                        if isinstance(existing_push, dict)
                        else existing_push
                    ),
                    "fix_suggestion": fix,
                }

        # 8. Acquire per-repository mutex lock
        repo_lock = _get_repo_push_lock(review.repository_id)
        async with repo_lock:
            # Re-check review state inside lock for concurrency safety
            review_fresh = self.review_service.get_review(review_id, user_id=user_id)
            if review_fresh:
                fresh_findings = list(review_fresh.findings_json or [])
                if finding_index < len(fresh_findings):
                    fresh_fix = fresh_findings[finding_index].get("fix_suggestion")
                    if fresh_fix and fresh_fix.get("git_push"):
                        f_push = fresh_fix["git_push"]
                        f_status = (
                            f_push.get("status")
                            if isinstance(f_push, dict)
                            else getattr(f_push, "status", None)
                        )
                        if f_status in (
                            GitPushStatusEnum.PUSHED.value,
                            GitPushStatusEnum.ALREADY_PUSHED.value,
                        ):
                            return {
                                "git_push": (
                                    GitPushResult(**f_push)
                                    if isinstance(f_push, dict)
                                    else f_push
                                ),
                                "fix_suggestion": fresh_fix,
                            }

            # 9. Resolve workspace root
            workspace_root = self._resolve_workspace_root(user_id, review.repository_id)

            # 10. Execute safe push via working tree manager
            push_result = self.working_tree_manager.push_isolated_branch(
                workspace_root=workspace_root,
                branch_name=branch_name,
                expected_commit_sha=commit_sha,
                remote_name=remote_name,
                expected_repo_url=repository.url,
            )

            # 11. Persist result
            updated_fix = self.review_service.update_finding_git_push_result(
                review_id=review_id,
                finding_index=finding_index,
                git_push_result=push_result,
                user_id=user_id,
            )

            return {
                "git_push": push_result,
                "fix_suggestion": updated_fix or fix,
            }
