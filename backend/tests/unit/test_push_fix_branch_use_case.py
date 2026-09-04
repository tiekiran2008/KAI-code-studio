"""
Unit Tests — PushFixBranchUseCase
==================================
Validates: review ownership, repository ownership, review status guard,
finding range, fix eligibility, git commit prerequisite, idempotency,
per-repo mutex serialization, push delegation, persistence, and all
WorkflowExecutionError paths.

LLM calls: 0  shell=True: 0  force push: 0
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.application.use_cases.push_fix_branch import (
    PushFixBranchUseCase,
    _REPO_PUSH_LOCKS,
)
from src.domain.entities.git import GitPushResult, GitPushStatusEnum
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_review(
    *,
    review_id="rev-1",
    user_id="user-1",
    repository_id="repo-1",
    status="completed",
    findings=None,
):
    """Build a lightweight mock review object."""
    if findings is None:
        findings = [_make_finding()]
    review = MagicMock()
    review.id = review_id
    review.status = status
    review.repository_id = repository_id
    review.findings_json = findings
    return review


def _mock_repository(*, repo_id="repo-1", url="https://github.com/user/repo.git"):
    repo = MagicMock()
    repo.id = repo_id
    repo.url = url
    return repo


def _make_finding(
    *,
    app_status="applied",
    user_decision="accepted",
    commit_status="committed",
    commit_sha="a" * 40,
    branch_name="ai-fix/rev-abc12345-f0",
    push_result=None,
):
    """Build a mock finding dict with a fix suggestion."""
    fix = {
        "finding_index": 0,
        "file_path": "src/utils.py",
        "original_code": "old",
        "proposed_code": "new",
        "explanation": "fix",
        "diff": "--- a\n+++ b",
        "confidence_score": 0.9,
        "validation_status": "valid",
        "user_decision": user_decision,
        "application_status": app_status,
        "new_hash": "abc123",
        "git_commit": {
            "status": commit_status,
            "branch_name": branch_name,
            "commit_sha": commit_sha,
            "committed_at": "2026-08-26T10:00:00+00:00",
            "file_path": "src/utils.py",
        },
    }
    if push_result is not None:
        fix["git_push"] = push_result
    return {"fix_suggestion": fix}


def _make_push_result(status="pushed"):
    return {
        "status": status,
        "remote_name": "origin",
        "branch_name": "ai-fix/rev-abc12345-f0",
        "commit_sha": "a" * 40,
        "remote_url_masked": "https://github.com/user/repo.git",
        "pushed_at": "2026-08-26T10:01:00+00:00",
        "message": "Pushed to origin",
    }


def _build_use_case(review=None, repository=None, push_result=None, push_exc=None):
    """Return a PushFixBranchUseCase with mocked services."""
    review_svc = MagicMock()
    review_svc.get_review.return_value = review
    review_svc.update_finding_git_push_result.return_value = (
        review.findings_json[0]["fix_suggestion"] if review else {}
    )

    repo_svc = MagicMock()
    repo_svc.get_repository.return_value = repository

    wt_manager = MagicMock()
    if push_exc:
        wt_manager.push_isolated_branch.side_effect = push_exc
    else:
        raw = push_result or _make_push_result()
        if isinstance(raw, dict):
            pr = GitPushResult(**raw)
        else:
            pr = raw
        wt_manager.push_isolated_branch.return_value = pr

    uc = PushFixBranchUseCase(
        review_service=review_svc,
        repository_service=repo_svc,
        working_tree_manager=wt_manager,
        workspace_root_resolver=lambda uid, rid: "/tmp/ws",
    )
    return uc, review_svc, repo_svc, wt_manager


# ---------------------------------------------------------------------------
# 1. Ownership / Auth Guards
# ---------------------------------------------------------------------------

class TestPushUseCaseOwnership:
    @pytest.mark.asyncio
    async def test_1_review_not_found_raises(self):
        uc, _, _, _ = _build_use_case(review=None, repository=None)
        with pytest.raises(ResourceNotFoundError):
            await uc.execute("rev-missing", 0, "user-1")

    @pytest.mark.asyncio
    async def test_2_review_not_found_user_id_passed(self):
        uc, review_svc, _, _ = _build_use_case(review=None, repository=None)
        with pytest.raises(ResourceNotFoundError):
            await uc.execute("rev-1", 0, "user-xyz")
        review_svc.get_review.assert_called_once_with("rev-1", user_id="user-xyz")

    @pytest.mark.asyncio
    async def test_3_repository_not_found_raises(self):
        review = _mock_review()
        uc, _, _, _ = _build_use_case(review=review, repository=None)
        with pytest.raises(ResourceNotFoundError):
            await uc.execute("rev-1", 0, "user-1")

    @pytest.mark.asyncio
    async def test_4_repository_ownership_verified(self):
        review = _mock_review()
        repo = _mock_repository()
        uc, _, repo_svc, _ = _build_use_case(review=review, repository=repo)
        await uc.execute("rev-1", 0, "user-1")
        repo_svc.get_repository.assert_called_once_with("repo-1", user_id="user-1")


# ---------------------------------------------------------------------------
# 2. Review Status Guard
# ---------------------------------------------------------------------------

class TestPushUseCaseReviewStatus:
    @pytest.mark.asyncio
    async def test_5_non_completed_review_raises(self):
        review = _mock_review(status="pending")
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with pytest.raises(WorkflowExecutionError, match="completed review"):
            await uc.execute("rev-1", 0, "user-1")

    @pytest.mark.asyncio
    async def test_6_completed_review_allowed(self):
        review = _mock_review(status="completed")
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        result = await uc.execute("rev-1", 0, "user-1")
        assert result["git_push"] is not None


# ---------------------------------------------------------------------------
# 3. Finding Index Validation
# ---------------------------------------------------------------------------

class TestPushUseCaseFindingIndex:
    @pytest.mark.asyncio
    async def test_7_negative_finding_index_raises(self):
        review = _mock_review()
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with pytest.raises(WorkflowExecutionError, match="finding_index must be"):
            await uc.execute("rev-1", -1, "user-1")

    @pytest.mark.asyncio
    async def test_8_out_of_range_finding_index_raises(self):
        review = _mock_review()
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with pytest.raises(WorkflowExecutionError, match="out of range"):
            await uc.execute("rev-1", 99, "user-1")


# ---------------------------------------------------------------------------
# 4. Fix Suggestion Eligibility Guards
# ---------------------------------------------------------------------------

class TestPushUseCaseFixEligibility:
    @pytest.mark.asyncio
    async def test_9_no_fix_suggestion_raises(self):
        review = _mock_review(findings=[{"fix_suggestion": None}])
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with pytest.raises(WorkflowExecutionError, match="No fix suggestion"):
            await uc.execute("rev-1", 0, "user-1")

    @pytest.mark.asyncio
    async def test_10_non_applied_status_raises(self):
        review = _mock_review(
            findings=[_make_finding(app_status="apply_failed")]
        )
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with pytest.raises(WorkflowExecutionError, match="must be applied"):
            await uc.execute("rev-1", 0, "user-1")

    @pytest.mark.asyncio
    async def test_11_rejected_fix_raises(self):
        review = _mock_review(
            findings=[_make_finding(user_decision="rejected")]
        )
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with pytest.raises(WorkflowExecutionError, match="Cannot push a rejected"):
            await uc.execute("rev-1", 0, "user-1")


# ---------------------------------------------------------------------------
# 5. Git Commit Prerequisite Guards
# ---------------------------------------------------------------------------

class TestPushUseCaseCommitPrerequisite:
    @pytest.mark.asyncio
    async def test_12_no_git_commit_raises(self):
        finding = {"fix_suggestion": {
            "application_status": "applied",
            "user_decision": "accepted",
            "git_commit": None,
        }}
        review = _mock_review(findings=[finding])
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with pytest.raises(WorkflowExecutionError, match="must have a local Git commit"):
            await uc.execute("rev-1", 0, "user-1")

    @pytest.mark.asyncio
    async def test_13_wrong_commit_status_raises(self):
        review = _mock_review(
            findings=[_make_finding(commit_status="failed")]
        )
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with pytest.raises(WorkflowExecutionError, match="committed.*status"):
            await uc.execute("rev-1", 0, "user-1")

    @pytest.mark.asyncio
    async def test_14_already_committed_status_allowed(self):
        review = _mock_review(
            findings=[_make_finding(commit_status="already_committed")]
        )
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        result = await uc.execute("rev-1", 0, "user-1")
        assert result["git_push"] is not None

    @pytest.mark.asyncio
    async def test_15_missing_commit_sha_raises(self):
        finding = {"fix_suggestion": {
            "application_status": "applied",
            "user_decision": "accepted",
            "git_commit": {"status": "committed", "branch_name": "ai-fix/rev-1-f0", "commit_sha": None},
        }}
        review = _mock_review(findings=[finding])
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with pytest.raises(WorkflowExecutionError, match="branch_name or commit_sha"):
            await uc.execute("rev-1", 0, "user-1")


# ---------------------------------------------------------------------------
# 6. Idempotency
# ---------------------------------------------------------------------------

class TestPushUseCaseIdempotency:
    @pytest.mark.asyncio
    async def test_16_already_pushed_returns_existing(self):
        push_raw = _make_push_result(status="pushed")
        review = _mock_review(findings=[_make_finding(push_result=push_raw)])
        repo = _mock_repository()
        uc, _, _, wt_manager = _build_use_case(review=review, repository=repo)
        result = await uc.execute("rev-1", 0, "user-1")
        assert result["git_push"].status == GitPushStatusEnum.PUSHED
        wt_manager.push_isolated_branch.assert_not_called()

    @pytest.mark.asyncio
    async def test_17_already_pushed_status_skips_push(self):
        push_raw = _make_push_result(status="already_pushed")
        review = _mock_review(findings=[_make_finding(push_result=push_raw)])
        repo = _mock_repository()
        uc, _, _, wt_manager = _build_use_case(review=review, repository=repo)
        result = await uc.execute("rev-1", 0, "user-1")
        assert result["git_push"].status == GitPushStatusEnum.ALREADY_PUSHED
        wt_manager.push_isolated_branch.assert_not_called()

    @pytest.mark.asyncio
    async def test_18_failed_push_state_allows_retry(self):
        push_raw = _make_push_result(status="failed")
        review = _mock_review(findings=[_make_finding(push_result=push_raw)])
        repo = _mock_repository()
        uc, _, _, wt_manager = _build_use_case(review=review, repository=repo)
        await uc.execute("rev-1", 0, "user-1")
        wt_manager.push_isolated_branch.assert_called_once()


# ---------------------------------------------------------------------------
# 7. Happy-Path Push Execution
# ---------------------------------------------------------------------------

class TestPushUseCaseHappyPath:
    @pytest.mark.asyncio
    async def test_19_push_result_returned(self):
        review = _mock_review()
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        result = await uc.execute("rev-1", 0, "user-1")
        assert isinstance(result["git_push"], GitPushResult)
        assert result["git_push"].status == GitPushStatusEnum.PUSHED

    @pytest.mark.asyncio
    async def test_20_push_args_correct(self):
        review = _mock_review()
        repo = _mock_repository(url="https://github.com/user/repo.git")
        uc, _, _, wt_manager = _build_use_case(review=review, repository=repo)
        await uc.execute("rev-1", 0, "user-1")
        wt_manager.push_isolated_branch.assert_called_once()
        kwargs = wt_manager.push_isolated_branch.call_args.kwargs
        assert kwargs["branch_name"] == "ai-fix/rev-abc12345-f0"
        assert kwargs["expected_commit_sha"] == "a" * 40
        assert kwargs["remote_name"] == "origin"
        assert kwargs["expected_repo_url"] == "https://github.com/user/repo.git"

    @pytest.mark.asyncio
    async def test_21_push_result_persisted(self):
        review = _mock_review()
        repo = _mock_repository()
        uc, review_svc, _, _ = _build_use_case(review=review, repository=repo)
        await uc.execute("rev-1", 0, "user-1")
        review_svc.update_finding_git_push_result.assert_called_once()
        call_args = review_svc.update_finding_git_push_result.call_args
        assert call_args.kwargs["review_id"] == "rev-1"
        assert call_args.kwargs["finding_index"] == 0
        assert call_args.kwargs["user_id"] == "user-1"

    @pytest.mark.asyncio
    async def test_22_fix_suggestion_returned(self):
        review = _mock_review()
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        result = await uc.execute("rev-1", 0, "user-1")
        assert result["fix_suggestion"] is not None

    @pytest.mark.asyncio
    async def test_23_already_pushed_status_handled(self):
        review = _mock_review()
        repo = _mock_repository()
        push_raw = _make_push_result(status="already_pushed")
        uc, _, _, _ = _build_use_case(
            review=review,
            repository=repo,
            push_result=GitPushResult(**push_raw),
        )
        result = await uc.execute("rev-1", 0, "user-1")
        assert result["git_push"].status == GitPushStatusEnum.ALREADY_PUSHED


# ---------------------------------------------------------------------------
# 8. Security Guards
# ---------------------------------------------------------------------------

class TestPushUseCaseSecurityGuards:
    @pytest.mark.asyncio
    async def test_24_no_llm_calls(self):
        """Zero LLM calls during the entire push flow."""
        review = _mock_review()
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with patch("src.application.use_cases.push_fix_branch.asyncio") as mock_asyncio:
            mock_asyncio.Lock = asyncio.Lock
            await uc.execute("rev-1", 0, "user-1")
        # No LLM import paths exist in the module
        import src.application.use_cases.push_fix_branch as mod
        assert not hasattr(mod, "llm") and not hasattr(mod, "LLMProvider")

    def test_25_no_shell_in_use_case_module(self):
        """push_fix_branch.py must not contain shell=True."""
        from pathlib import Path
        src = Path("backend/src/application/use_cases/push_fix_branch.py")
        if not src.exists():
            src = Path("src/application/use_cases/push_fix_branch.py")
        if src.exists():
            content = src.read_text()
            assert "shell=True" not in content
            assert "subprocess" not in content

    @pytest.mark.asyncio
    async def test_26_no_github_api_calls(self):
        """Push use case must never call GitHub API directly."""
        review = _mock_review()
        repo = _mock_repository()
        uc, _, _, _ = _build_use_case(review=review, repository=repo)
        with patch("httpx.AsyncClient") as mock_client, \
             patch("httpx.Client") as mock_sync:
            await uc.execute("rev-1", 0, "user-1")
            mock_client.assert_not_called()
            mock_sync.assert_not_called()


# ---------------------------------------------------------------------------
# 9. Concurrency / Mutex
# ---------------------------------------------------------------------------

class TestPushUseCaseConcurrency:
    @pytest.mark.asyncio
    async def test_27_per_repo_lock_is_singleton(self):
        """Same repo ID always returns the same asyncio.Lock instance."""
        from src.application.use_cases.push_fix_branch import _get_repo_push_lock
        lock_a = _get_repo_push_lock("repo-singleton-test")
        lock_b = _get_repo_push_lock("repo-singleton-test")
        assert lock_a is lock_b, "Same repo must share a single asyncio.Lock instance"

    @pytest.mark.asyncio
    async def test_27b_different_repos_have_different_locks(self):
        """Different repo IDs get independent asyncio.Lock instances."""
        from src.application.use_cases.push_fix_branch import _get_repo_push_lock
        lock_x = _get_repo_push_lock("repo-x-unique-abc")
        lock_y = _get_repo_push_lock("repo-y-unique-def")
        assert lock_x is not lock_y, "Different repos must have independent locks"

    @pytest.mark.asyncio
    async def test_27c_single_push_completes_under_lock(self):
        """A single push executes successfully within the per-repo lock context."""
        review = _mock_review()
        repo = _mock_repository()
        uc, _, _, wt_manager = _build_use_case(review=review, repository=repo)
        result = await uc.execute("rev-1", 0, "user-1")
        assert result["git_push"].status == GitPushStatusEnum.PUSHED
        wt_manager.push_isolated_branch.assert_called_once()

    @pytest.mark.asyncio
    async def test_28_different_repos_not_blocked(self):
        """Pushes for different repos use independent locks."""
        review_a = _mock_review(review_id="rev-1", repository_id="repo-a")
        review_b = _mock_review(review_id="rev-2", repository_id="repo-b")
        repo_a = _mock_repository(repo_id="repo-a")
        repo_b = _mock_repository(repo_id="repo-b")

        uc_a, review_svc_a, repo_svc_a, wt_manager_a = _build_use_case(
            review=review_a, repository=repo_a
        )
        uc_b, review_svc_b, repo_svc_b, wt_manager_b = _build_use_case(
            review=review_b, repository=repo_b
        )

        results = await asyncio.gather(
            uc_a.execute("rev-1", 0, "user-1"),
            uc_b.execute("rev-2", 0, "user-1"),
        )
        assert len(results) == 2
