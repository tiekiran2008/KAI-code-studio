"""
Unit Tests: Apply Fix Suggestion Use Case
=========================================
Validates authorization, pre-conditions, state transitions, idempotency,
concurrency safety, and compensating rollback in ApplyFixSuggestionUseCase.
"""
import asyncio
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.application.use_cases.apply_fix import ApplyFixSuggestionUseCase
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService
from src.application.services.atomic_patcher import AtomicFilePatcher
from src.domain.entities.code_review import ReviewStatusEnum
from src.domain.entities.fix_suggestion import (
    FixSuggestion,
    FixUserDecision,
    FixValidationStatus,
    FixApplicationStatus,
)
from src.domain.entities.patch import PatchResult, StaleSourceError, AmbiguousMatchError
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError


class FakeReview:
    def __init__(self, id, user_id, repository_id, status, findings_json):
        self.id = id
        self.user_id = user_id
        self.repository_id = repository_id
        self.status = status
        self.findings_json = findings_json


class FakeRepo:
    def __init__(self, id, user_id):
        self.id = id
        self.user_id = user_id


@pytest.fixture
def mock_deps(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    target_file = workspace / "math.py"
    target_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    review_service = MagicMock(spec=CodeReviewService)
    repository_service = MagicMock(spec=RepositoryService)
    atomic_patcher = AtomicFilePatcher()

    use_case = ApplyFixSuggestionUseCase(
        review_service=review_service,
        repository_service=repository_service,
        atomic_patcher=atomic_patcher,
        workspace_root_resolver=lambda u, r: str(workspace),
    )

    return {
        "use_case": use_case,
        "review_service": review_service,
        "repository_service": repository_service,
        "atomic_patcher": atomic_patcher,
        "workspace": workspace,
        "target_file": target_file,
    }


def _make_finding(
    decision=FixUserDecision.ACCEPTED,
    validation=FixValidationStatus.VALID,
    app_status=FixApplicationStatus.NOT_APPLIED,
    file_path="math.py",
    orig="return a + b",
    prop="return a * b",
):
    return {
        "issue": "Use multiplication",
        "severity": "medium",
        "file_path": file_path,
        "line_number": 2,
        "fix_suggestion": {
            "finding_index": 0,
            "file_path": file_path,
            "original_code": orig,
            "proposed_code": prop,
            "explanation": "Multiply instead of add",
            "diff": "--- a\n+++ b",
            "confidence_score": 1.0,
            "validation_status": validation.value if hasattr(validation, "value") else str(validation),
            "user_decision": decision.value if hasattr(decision, "value") else str(decision),
            "application_status": app_status.value if hasattr(app_status, "value") else str(app_status),
        },
    }


@pytest.mark.asyncio
async def test_apply_fix_happy_path(mock_deps):
    use_case = mock_deps["use_case"]
    review_svc = mock_deps["review_service"]
    repo_svc = mock_deps["repository_service"]
    target_file = mock_deps["target_file"]

    review = FakeReview("rev-1", "user-1", "repo-1", ReviewStatusEnum.COMPLETED.value, [_make_finding()])
    review_svc.get_review.return_value = review
    repo_svc.get_repository.return_value = FakeRepo("repo-1", "user-1")

    # Mock updating DB
    def fake_update(review_id, finding_index, application_status, applied_at=None, previous_hash=None, new_hash=None, user_id=None, application_error=None):
        return {
            "finding_index": finding_index,
            "application_status": application_status.value,
            "applied_at": applied_at,
            "previous_hash": previous_hash,
            "new_hash": new_hash,
        }
    review_svc.update_finding_application_status.side_effect = fake_update

    result = await use_case.execute("rev-1", 0, "user-1")

    assert result["idempotent"] is False
    assert result["fix_suggestion"]["application_status"] == "applied"
    assert "return a * b" in target_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_apply_fix_rejected_when_not_accepted(mock_deps):
    use_case = mock_deps["use_case"]
    review_svc = mock_deps["review_service"]
    repo_svc = mock_deps["repository_service"]

    # Decision is pending
    review = FakeReview(
        "rev-1", "user-1", "repo-1", ReviewStatusEnum.COMPLETED.value,
        [_make_finding(decision=FixUserDecision.PENDING)]
    )
    review_svc.get_review.return_value = review
    repo_svc.get_repository.return_value = FakeRepo("repo-1", "user-1")

    with pytest.raises(WorkflowExecutionError, match="must be accepted before applying"):
        await use_case.execute("rev-1", 0, "user-1")

    # Decision is rejected
    review.findings_json = [_make_finding(decision=FixUserDecision.REJECTED)]
    with pytest.raises(WorkflowExecutionError, match="must be accepted before applying"):
        await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_apply_fix_rejected_when_validation_invalid(mock_deps):
    use_case = mock_deps["use_case"]
    review_svc = mock_deps["review_service"]
    repo_svc = mock_deps["repository_service"]

    review = FakeReview(
        "rev-1", "user-1", "repo-1", ReviewStatusEnum.COMPLETED.value,
        [_make_finding(validation=FixValidationStatus.INVALID)]
    )
    review_svc.get_review.return_value = review
    repo_svc.get_repository.return_value = FakeRepo("repo-1", "user-1")

    with pytest.raises(WorkflowExecutionError, match="invalid syntax validation"):
        await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_apply_fix_rejected_when_review_not_completed(mock_deps):
    use_case = mock_deps["use_case"]
    review_svc = mock_deps["review_service"]
    repo_svc = mock_deps["repository_service"]

    for st in [ReviewStatusEnum.PENDING, ReviewStatusEnum.IN_PROGRESS, ReviewStatusEnum.FAILED, ReviewStatusEnum.CANCELLED]:
        review = FakeReview("rev-1", "user-1", "repo-1", st.value, [_make_finding()])
        review_svc.get_review.return_value = review
        repo_svc.get_repository.return_value = FakeRepo("repo-1", "user-1")

        with pytest.raises(WorkflowExecutionError, match="requires a completed review"):
            await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_apply_fix_unauthorized_user_blocked(mock_deps):
    use_case = mock_deps["use_case"]
    review_svc = mock_deps["review_service"]
    repo_svc = mock_deps["repository_service"]

    # Review ownership mismatch -> returns None
    review_svc.get_review.return_value = None
    with pytest.raises(ResourceNotFoundError, match="Review not found"):
        await use_case.execute("rev-1", 0, "user-2")

    # Repo ownership mismatch -> returns None
    review = FakeReview("rev-1", "user-1", "repo-1", ReviewStatusEnum.COMPLETED.value, [_make_finding()])
    review_svc.get_review.return_value = review
    repo_svc.get_repository.return_value = None
    with pytest.raises(ResourceNotFoundError, match="Repository not found"):
        await use_case.execute("rev-1", 0, "user-1")


@pytest.mark.asyncio
async def test_apply_fix_idempotent_when_already_applied(mock_deps):
    use_case = mock_deps["use_case"]
    review_svc = mock_deps["review_service"]
    repo_svc = mock_deps["repository_service"]

    review = FakeReview(
        "rev-1", "user-1", "repo-1", ReviewStatusEnum.COMPLETED.value,
        [_make_finding(app_status=FixApplicationStatus.APPLIED)]
    )
    review_svc.get_review.return_value = review
    repo_svc.get_repository.return_value = FakeRepo("repo-1", "user-1")

    result = await use_case.execute("rev-1", 0, "user-1")
    assert result["idempotent"] is True
    assert result["fix_suggestion"]["application_status"] == "applied"


@pytest.mark.asyncio
async def test_apply_fix_stale_source_updates_status(mock_deps):
    use_case = mock_deps["use_case"]
    review_svc = mock_deps["review_service"]
    repo_svc = mock_deps["repository_service"]
    target_file = mock_deps["target_file"]

    # Finding expects snippet that doesn't exist in file
    review = FakeReview(
        "rev-1", "user-1", "repo-1", ReviewStatusEnum.COMPLETED.value,
        [_make_finding(orig="def non_existent():")]
    )
    review_svc.get_review.return_value = review
    repo_svc.get_repository.return_value = FakeRepo("repo-1", "user-1")

    with pytest.raises(WorkflowExecutionError, match="Stale source detected"):
        await use_case.execute("rev-1", 0, "user-1")

    # Verify status updated to STALE in DB
    review_svc.update_finding_application_status.assert_called_once()
    call_args = review_svc.update_finding_application_status.call_args
    assert (
        call_args.kwargs.get("application_status") == FixApplicationStatus.STALE
        or (len(call_args.args) > 2 and call_args.args[2] == FixApplicationStatus.STALE)
    )


@pytest.mark.asyncio
async def test_apply_fix_concurrency_race_executes_patch_only_once(mock_deps):
    use_case = mock_deps["use_case"]
    review_svc = mock_deps["review_service"]
    repo_svc = mock_deps["repository_service"]
    target_file = mock_deps["target_file"]

    # Shared mutable findings state simulating real DB
    current_findings = [_make_finding()]

    def mock_get_review(review_id, user_id=None):
        return FakeReview(review_id, user_id, "repo-1", ReviewStatusEnum.COMPLETED.value, current_findings)

    def mock_update(review_id, finding_index, application_status, applied_at=None, previous_hash=None, new_hash=None, user_id=None, application_error=None):
        updated = dict(current_findings[finding_index]["fix_suggestion"])
        updated["application_status"] = application_status.value
        updated["applied_at"] = applied_at
        current_findings[finding_index]["fix_suggestion"] = updated
        return updated

    review_svc.get_review.side_effect = mock_get_review
    review_svc.update_finding_application_status.side_effect = mock_update
    repo_svc.get_repository.return_value = FakeRepo("repo-1", "user-1")

    # Run two concurrent applies
    res1, res2 = await asyncio.gather(
        use_case.execute("rev-1", 0, "user-1"),
        use_case.execute("rev-1", 0, "user-1"),
    )

    # One should be fresh apply, the second should be idempotent
    results = [res1["idempotent"], res2["idempotent"]]
    assert False in results
    assert True in results
    assert "return a * b" in target_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_apply_fix_compensating_rollback_on_db_failure(mock_deps):
    use_case = mock_deps["use_case"]
    review_svc = mock_deps["review_service"]
    repo_svc = mock_deps["repository_service"]
    target_file = mock_deps["target_file"]
    original_content = target_file.read_text(encoding="utf-8")

    review = FakeReview("rev-1", "user-1", "repo-1", ReviewStatusEnum.COMPLETED.value, [_make_finding()])
    review_svc.get_review.return_value = review
    repo_svc.get_repository.return_value = FakeRepo("repo-1", "user-1")

    # DB update raises error after file patch
    review_svc.update_finding_application_status.side_effect = RuntimeError("DB connection lost")

    with pytest.raises(WorkflowExecutionError, match="compensating rollback executed"):
        await use_case.execute("rev-1", 0, "user-1")

    # Target file should be rolled back to original content
    assert target_file.read_text(encoding="utf-8") == original_content


def test_fix_suggestion_backward_compatibility():
    """Verify pre-11.3 FixSuggestion JSON without application_status defaults to NOT_APPLIED."""
    legacy_json = {
        "finding_index": 0,
        "file_path": "math.py",
        "original_code": "return a + b",
        "proposed_code": "return a * b",
        "explanation": "Multiply instead",
        "confidence_score": 0.9,
    }
    suggestion = FixSuggestion(**legacy_json)
    assert suggestion.application_status == FixApplicationStatus.NOT_APPLIED
    assert suggestion.applied_at is None
    assert suggestion.application_error is None
    assert suggestion.previous_hash is None
    assert suggestion.new_hash is None
