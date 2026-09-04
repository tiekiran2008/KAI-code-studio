"""
Unit Tests — CommitAppliedFixUseCase
====================================
Validates ownership enforcement, eligibility checks, Tier-1 prerequisites,
stale source detection, idempotency, persistence, and concurrency safety.
"""
import asyncio
import hashlib
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import MagicMock
import pytest

from src.core.errors import ResourceNotFoundError, WorkflowExecutionError
from src.domain.entities.git import GitCommitStatusEnum, GitCommitResult
from src.domain.entities.fix_suggestion import FixApplicationStatus, FixUserDecision
from src.domain.entities.verification import VerificationStatus
from src.application.use_cases.commit_applied_fix import CommitAppliedFixUseCase
from src.infrastructure.git.working_tree_manager import GitWorkingTreeManager


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=str(path), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-m", "Initial commit"],
        cwd=str(path),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _setup_workspace_and_fix(workspace: Path, app_status="applied", static_status="passed", user_dec="accepted"):
    _init_git_repo(workspace)

    # Initial file
    file_path = workspace / "src" / "utils.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    initial_bytes = b"def greet(name):\n    return f'Hello {name}'\n"
    file_path.write_bytes(initial_bytes)

    subprocess.run(["git", "add", "src/utils.py"], cwd=str(workspace), check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "add utils"],
        cwd=str(workspace),
        check=True,
    )

    # Applied fix on disk
    fixed_bytes = b"def greet(name: str) -> str:\n    return f'Hello {name}'\n"
    file_path.write_bytes(fixed_bytes)
    content_hash = hashlib.sha256(fixed_bytes).hexdigest()

    fix_dict = {
        "finding_index": 0,
        "file_path": "src/utils.py",
        "original_code": "def greet(name):\n    return f'Hello {name}'",
        "proposed_code": "def greet(name: str) -> str:\n    return f'Hello {name}'",
        "explanation": "Add type hints",
        "diff": "--- a/src/utils.py\n+++ b/src/utils.py",
        "confidence_score": 0.95,
        "validation_status": "valid",
        "user_decision": user_dec,
        "application_status": app_status,
        "new_hash": content_hash,
        "static_verification": {"status": static_status} if static_status else None,
    }

    return fix_dict, content_hash


def _make_mock_review(fix_dict, review_id="rev-1", repo_id="repo-1", status="completed"):
    review = MagicMock()
    review.id = review_id
    review.repository_id = repo_id
    review.status = status
    review.findings_json = [{"issue": "Missing type hints", "fix_suggestion": fix_dict}]
    return review


class MockReviewService:
    def __init__(self, review=None):
        self._review = review
        self.last_git_result = None

    def get_review(self, review_id, user_id=None):
        return self._review

    def update_finding_git_commit_result(self, review_id, finding_index, git_commit_result, user_id=None):
        self.last_git_result = git_commit_result
        existing = self._review.findings_json[finding_index]["fix_suggestion"]
        updated = dict(existing)
        if hasattr(git_commit_result, "model_dump"):
            updated["git_commit"] = git_commit_result.model_dump(mode="json")
        elif isinstance(git_commit_result, dict):
            updated["git_commit"] = git_commit_result
        return updated


class MockRepoService:
    def __init__(self, found=True):
        self._found = found

    def get_repository(self, user_id, repo_id):
        if not self._found:
            return None
        repo = MagicMock()
        repo.id = repo_id
        return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_commit_use_case_happy_path(tmp_path):
    """Full happy path: applied fix with static verification passed creates local commit."""
    fix_dict, _ = _setup_workspace_and_fix(tmp_path)
    review = _make_mock_review(fix_dict)
    review_svc = MockReviewService(review)

    use_case = CommitAppliedFixUseCase(
        review_service=review_svc,
        repository_service=MockRepoService(),
        workspace_root_resolver=lambda u, r: str(tmp_path),
    )

    result = await use_case.execute("rev-1", 0, "user-1")

    assert result["git_commit"].status == GitCommitStatusEnum.COMMITTED
    assert result["git_commit"].commit_sha is not None
    assert len(result["git_commit"].commit_sha) == 40
    assert "ai-fix/" in result["git_commit"].branch_name
    assert review_svc.last_git_result is not None


@pytest.mark.asyncio
async def test_commit_use_case_review_not_found():
    use_case = CommitAppliedFixUseCase(
        review_service=MockReviewService(review=None),
        repository_service=MockRepoService(),
    )
    with pytest.raises(ResourceNotFoundError, match="Review not found"):
        await use_case.execute("rev-unknown", 0, "user-1")


@pytest.mark.asyncio
async def test_commit_use_case_negative_index():
    use_case = CommitAppliedFixUseCase(
        review_service=MockReviewService(),
        repository_service=MockRepoService(),
    )
    with pytest.raises(WorkflowExecutionError, match="finding_index must be >= 0"):
        await use_case.execute("rev-1", -1, "user-1")


@pytest.mark.asyncio
async def test_commit_use_case_not_applied_fix(tmp_path):
    fix_dict, _ = _setup_workspace_and_fix(tmp_path, app_status="not_applied")
    review = _make_mock_review(fix_dict)
    use_case = CommitAppliedFixUseCase(
        review_service=MockReviewService(review),
        repository_service=MockRepoService(),
        workspace_root_resolver=lambda u, r: str(tmp_path),
    )
    with pytest.raises(WorkflowExecutionError, match="must be applied"):
        await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_commit_use_case_rejected_fix(tmp_path):
    fix_dict, _ = _setup_workspace_and_fix(tmp_path, user_dec="rejected")
    review = _make_mock_review(fix_dict)
    use_case = CommitAppliedFixUseCase(
        review_service=MockReviewService(review),
        repository_service=MockRepoService(),
        workspace_root_resolver=lambda u, r: str(tmp_path),
    )
    with pytest.raises(WorkflowExecutionError, match="Cannot commit a rejected"):
        await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_commit_use_case_tier1_prerequisite_required(tmp_path):
    """Static verification must be 'passed' before committing to Git."""
    fix_dict, _ = _setup_workspace_and_fix(tmp_path, static_status="failed")
    review = _make_mock_review(fix_dict)
    use_case = CommitAppliedFixUseCase(
        review_service=MockReviewService(review),
        repository_service=MockRepoService(),
        workspace_root_resolver=lambda u, r: str(tmp_path),
    )
    with pytest.raises(WorkflowExecutionError, match="static verification must"):
        await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_commit_use_case_stale_source_detected(tmp_path):
    """Modifying the file after apply triggers stale source rejection."""
    fix_dict, _ = _setup_workspace_and_fix(tmp_path)
    # Corrupt target file on disk
    (tmp_path / "src" / "utils.py").write_text("corrupted content\n")
    review = _make_mock_review(fix_dict)
    use_case = CommitAppliedFixUseCase(
        review_service=MockReviewService(review),
        repository_service=MockRepoService(),
        workspace_root_resolver=lambda u, r: str(tmp_path),
    )
    with pytest.raises(WorkflowExecutionError, match="Source file was modified after fix"):
        await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_commit_use_case_idempotent(tmp_path):
    """Repeated calls return existing commit without creating duplicates."""
    fix_dict, _ = _setup_workspace_and_fix(tmp_path)
    review = _make_mock_review(fix_dict)
    review_svc = MockReviewService(review)

    use_case = CommitAppliedFixUseCase(
        review_service=review_svc,
        repository_service=MockRepoService(),
        workspace_root_resolver=lambda u, r: str(tmp_path),
    )

    # First commit
    res1 = await use_case.execute("rev-1", 0, "user-1")
    sha1 = res1["git_commit"].commit_sha

    # Update review mock with persisted commit
    review.findings_json[0]["fix_suggestion"]["git_commit"] = res1["git_commit"].model_dump(mode="json")

    # Second commit
    res2 = await use_case.execute("rev-1", 0, "user-1")
    sha2 = res2["git_commit"].commit_sha

    assert sha1 == sha2


@pytest.mark.asyncio
async def test_commit_use_case_concurrency(tmp_path):
    """Concurrent commit requests for the same repository serialize safely."""
    fix_dict, _ = _setup_workspace_and_fix(tmp_path)
    review = _make_mock_review(fix_dict)
    review_svc = MockReviewService(review)

    use_case = CommitAppliedFixUseCase(
        review_service=review_svc,
        repository_service=MockRepoService(),
        workspace_root_resolver=lambda u, r: str(tmp_path),
    )

    # Run two simultaneous executions
    results = await asyncio.gather(
        use_case.execute("rev-1", 0, "user-1"),
        use_case.execute("rev-1", 0, "user-1"),
    )

    assert results[0]["git_commit"].status in (GitCommitStatusEnum.COMMITTED, GitCommitStatusEnum.ALREADY_COMMITTED)
    assert results[1]["git_commit"].status in (GitCommitStatusEnum.COMMITTED, GitCommitStatusEnum.ALREADY_COMMITTED)
