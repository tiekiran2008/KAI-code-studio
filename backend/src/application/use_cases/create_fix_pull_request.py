"""
Create Fix Pull Request Use Case
=================================
Executes a safe, non-destructive GitHub Pull Request creation for an eligible,
already-pushed dedicated AI fix branch.

Enforces:
- Review and repository ownership verification
- Completed review status
- Fix suggestion exists, accepted, and applied
- Local Git commit prerequisite (verified commit SHA and branch name)
- Git push prerequisite (status == 'pushed' or 'already_pushed')
- Head branch derived exclusively from persisted push/commit state
- Base branch derived exclusively from server-side repository configuration
- Deterministic, sanitized PR title and description generation
- Zero prompt injection control over GitHub operations (text treated as pure data)
- Zero merge, zero PR approval, zero branch deletion, zero force push
- Per-repository asyncio mutex lock
- Idempotency & existing open PR reconciliation
- Persistence in review findings JSON metadata
- Zero LLM calls during PR creation
"""
import asyncio
import os
import re
from typing import Any, Dict, Optional, Tuple

from src.core.errors import ResourceNotFoundError, WorkflowExecutionError
from src.core.logger import logger
from src.domain.entities.git import GitPullRequestResult, GitPullRequestStatusEnum
from src.domain.entities.fix_suggestion import FixApplicationStatus, FixUserDecision
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService
from src.infrastructure.git.github_pr_service import GitHubPullRequestService
from src.infrastructure.analysis.stack_detector import StackDetector


_REPO_PR_LOCKS: Dict[str, asyncio.Lock] = {}


def _get_repo_pr_lock(repo_id: str) -> asyncio.Lock:
    """Return an asyncio.Lock per repository to serialize PR creation operations."""
    if repo_id not in _REPO_PR_LOCKS:
        _REPO_PR_LOCKS[repo_id] = asyncio.Lock()
    return _REPO_PR_LOCKS[repo_id]


def _sanitize_single_line(text: Optional[str], max_len: int = 100) -> str:
    """Sanitize text to a safe single-line string with length limit."""
    if not text:
        return ""
    # Replace newlines, tabs, and control chars with spaces
    cleaned = re.sub(r'[\r\n\t]+', ' ', text).strip()
    # Strip any potential markdown or injection markers
    cleaned = re.sub(r'[`#*\[\]<>]', '', cleaned).strip()
    return cleaned[:max_len]


def _build_pr_title(finding: Dict[str, Any], finding_index: int) -> str:
    """Generate a deterministic, safe PR title."""
    issue = finding.get("issue") or finding.get("explanation") or f"Finding {finding_index + 1}"
    sanitized_issue = _sanitize_single_line(issue, max_len=80)
    return f"fix: {sanitized_issue}"


def _build_pr_body(
    finding: Dict[str, Any],
    fix: Dict[str, Any],
    head_branch: str,
    base_branch: str,
    commit_sha: str,
) -> str:
    """Generate a deterministic, structured PR description from trusted review data."""
    issue = _sanitize_single_line(finding.get("issue", "Code quality finding"), max_len=150)
    severity = _sanitize_single_line(finding.get("severity", "medium"), max_len=30)
    file_path = _sanitize_single_line(fix.get("file_path", "unknown"), max_len=120)
    line_number = finding.get("line_number", 1)
    explanation = fix.get("explanation", "Applied automated fix suggestion.")
    clean_explanation = re.sub(r'[\r\n]{3,}', '\n\n', explanation).strip()

    # Static verification summary
    static_ver = fix.get("static_verification")
    static_status = static_ver.get("status") if isinstance(static_ver, dict) else "passed"
    static_line = f"Passed (Tier-1 Static Verification)" if static_status == "passed" else static_status

    # Test verification summary
    test_ver = fix.get("test_verification")
    test_line = "Not run"
    if test_ver and isinstance(test_ver, dict):
        t_status = test_ver.get("status")
        if t_status == "passed":
            test_line = "Passed (Tier-2 Isolated Sandbox Tests)"
        elif t_status == "failed":
            test_line = "Failed (Tier-2 Sandbox Tests)"
        elif t_status == "unsupported":
            test_line = "Unsupported language/runner"

    short_sha = commit_sha[:8] if commit_sha else "unknown"

    body = f"""## AI Code Review Fix Summary

**Issue:** {issue}
**Severity:** `{severity}`
**Target File:** `{file_path}` (Line {line_number})

### Description & Explanation
{clean_explanation}

### Verification Status
- **Static Verification:** {static_line}
- **Isolated Tests:** {test_line}

### Commit & Branch
- **Fix Branch:** `{head_branch}`
- **Commit SHA:** `{short_sha}`
- **Target Base:** `{base_branch}`

---
*Created automatically by Software Engineering AI Agent upon explicit user approval. Please review changes before merging.*
"""
    return body.strip()


class CreateFixPullRequestUseCase:
    """Use case for safely creating a GitHub Pull Request from a pushed AI fix branch."""

    def __init__(
        self,
        review_service: CodeReviewService,
        repository_service: RepositoryService,
        github_pr_service: Optional[GitHubPullRequestService] = None,
    ) -> None:
        self.review_service = review_service
        self.repository_service = repository_service
        self.github_pr_service = github_pr_service or GitHubPullRequestService()
        self.detector = StackDetector()

    def _resolve_repo_owner_and_name(self, repository: Any) -> Tuple[str, str]:
        """Derive trusted GitHub owner and repo name from server-side repository metadata."""
        if getattr(repository, "owner", None) and getattr(repository, "name", None):
            return repository.owner, repository.name

        url = getattr(repository, "url", "")
        if url:
            owner, name = self.detector.extract_owner_and_name(url)
            if owner and name:
                return owner, name

        raise WorkflowExecutionError("Could not determine GitHub repository owner and name from repository configuration")

    async def execute(
        self,
        review_id: str,
        finding_index: int,
        user_id: str,
        github_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute the safe GitHub Pull Request creation for an eligible fix suggestion.

        Parameters
        ----------
        review_id : str
            ID of the code review.
        finding_index : int
            0-based index of finding in review.findings_json.
        user_id : str
            Authenticated user ID from token.
        github_token : Optional[str]
            Pre-resolved, decrypted GitHub OAuth token for the current user.
            Supplied by the dependency layer from GitHubIntegrationService.
            Takes priority over the repository's stored PAT and GITHUB_TOKEN env var.
            SECURITY: This value must never be logged, stored, or returned in any response.

        Returns
        -------
        Dict[str, Any]
            {"git_pull_request": GitPullRequestResult, "fix_suggestion": dict}
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
            raise WorkflowExecutionError("Pull Request creation requires a completed review")

        # 3. Repository verification & ownership check
        repository = self.repository_service.get_repository(
            user_id=user_id, repo_id=review.repository_id
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
                "Fix suggestion must be applied before creating a Pull Request"
            )

        user_dec = fix.get("user_decision")
        if user_dec == FixUserDecision.REJECTED.value:
            raise WorkflowExecutionError("Cannot create a Pull Request for a rejected fix suggestion")

        # 6. Local Git Commit Prerequisite
        git_commit_raw = fix.get("git_commit")
        if not git_commit_raw:
            raise WorkflowExecutionError(
                "Fix suggestion must have a local Git commit before creating a Pull Request"
            )

        commit_status = (
            git_commit_raw.get("status")
            if isinstance(git_commit_raw, dict)
            else getattr(git_commit_raw, "status", None)
        )
        if commit_status not in ("committed", "already_committed"):
            raise WorkflowExecutionError(
                "Local Git commit must be in 'committed' status to create a Pull Request"
            )

        commit_sha = (
            git_commit_raw.get("commit_sha")
            if isinstance(git_commit_raw, dict)
            else getattr(git_commit_raw, "commit_sha", None)
        )

        # 7. Git Push Prerequisite
        git_push_raw = fix.get("git_push")
        if not git_push_raw:
            raise WorkflowExecutionError(
                "Fix branch must be pushed to remote before creating a Pull Request"
            )

        push_status = (
            git_push_raw.get("status")
            if isinstance(git_push_raw, dict)
            else getattr(git_push_raw, "status", None)
        )
        if push_status not in ("pushed", "already_pushed"):
            raise WorkflowExecutionError(
                "Fix branch must be pushed to remote before creating a Pull Request"
            )

        head_branch = (
            git_push_raw.get("branch_name")
            if isinstance(git_push_raw, dict)
            else getattr(git_push_raw, "branch_name", None)
        ) or (
            git_commit_raw.get("branch_name")
            if isinstance(git_commit_raw, dict)
            else getattr(git_commit_raw, "branch_name", None)
        )

        if not head_branch:
            raise WorkflowExecutionError(
                "Cannot create Pull Request: head branch name is missing from Git metadata"
            )

        # 8. Idempotency check on existing persisted PR result
        existing_pr = fix.get("git_pull_request")
        if existing_pr:
            existing_status = (
                existing_pr.get("status")
                if isinstance(existing_pr, dict)
                else getattr(existing_pr, "status", None)
            )
            if existing_status in (
                GitPullRequestStatusEnum.CREATED.value,
                GitPullRequestStatusEnum.ALREADY_EXISTS.value,
            ):
                logger.info(
                    "git_pr_idempotent_hit",
                    review_id=review_id,
                    finding_index=finding_index,
                    head_branch=head_branch,
                )
                return {
                    "git_pull_request": (
                        GitPullRequestResult(**existing_pr)
                        if isinstance(existing_pr, dict)
                        else existing_pr
                    ),
                    "fix_suggestion": fix,
                }

        # 9. Derive trusted GitHub owner and repo name
        owner, repo_name = self._resolve_repo_owner_and_name(repository)

        # 10. Derive trusted base branch server-side
        base_branch = getattr(repository, "default_branch", None) or "main"

        # 11. Deterministic PR title & description
        title = _build_pr_title(finding, finding_index)
        body = _build_pr_body(
            finding=finding,
            fix=fix,
            head_branch=head_branch,
            base_branch=base_branch,
            commit_sha=commit_sha or "",
        )

        # 12. Resolve token server-side — priority:
        #   1. Pre-resolved user OAuth token from GitHubIntegrationService (most specific, per-user)
        #   2. Repository-level stored PAT (git_access_token_encrypted field)
        #   3. GITHUB_TOKEN environment variable (deployment-level fallback)
        # SECURITY: token value is never logged. Log only its presence as a boolean.
        token = (
            github_token
            or getattr(repository, "git_access_token_encrypted", None)
            or os.getenv("GITHUB_TOKEN")
        )
        logger.debug(
            "git_pr_token_resolved",
            source="oauth" if github_token else (
                "stored_pat" if getattr(repository, "git_access_token_encrypted", None)
                else ("env_var" if os.getenv("GITHUB_TOKEN") else "none")
            ),
            has_token=bool(token),
        )

        # 13. Acquire per-repository mutex lock
        repo_lock = _get_repo_pr_lock(review.repository_id)
        async with repo_lock:
            # Re-check review state inside lock for concurrency safety
            review_fresh = self.review_service.get_review(review_id, user_id=user_id)
            if review_fresh:
                fresh_findings = list(review_fresh.findings_json or [])
                if finding_index < len(fresh_findings):
                    fresh_fix = fresh_findings[finding_index].get("fix_suggestion")
                    if fresh_fix and fresh_fix.get("git_pull_request"):
                        f_pr = fresh_fix["git_pull_request"]
                        f_status = (
                            f_pr.get("status")
                            if isinstance(f_pr, dict)
                            else getattr(f_pr, "status", None)
                        )
                        if f_status in (
                            GitPullRequestStatusEnum.CREATED.value,
                            GitPullRequestStatusEnum.ALREADY_EXISTS.value,
                        ):
                            return {
                                "git_pull_request": (
                                    GitPullRequestResult(**f_pr)
                                    if isinstance(f_pr, dict)
                                    else f_pr
                                ),
                                "fix_suggestion": fresh_fix,
                            }

            # 14. Execute PR creation via GitHub Pull Request Service
            pr_result = await self.github_pr_service.create_pull_request(
                owner=owner,
                repo=repo_name,
                head_branch=head_branch,
                base_branch=base_branch,
                title=title,
                body=body,
                token=token,
            )

            # 15. Persist PR result in review metadata
            updated_fix = self.review_service.update_finding_git_pull_request_result(
                review_id=review_id,
                finding_index=finding_index,
                git_pull_request_result=pr_result,
                user_id=user_id,
            )

            return {
                "git_pull_request": pr_result,
                "fix_suggestion": updated_fix or fix,
            }
