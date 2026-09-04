"""
Unit tests for VerifyAppliedFixUseCase
======================================
Tests the orchestration of Tier-1 in-memory verification on applied fixes.
Validates ownership enforcement, read-only guarantees, source-changed tracking,
and zero LLM/subprocess execution.
"""
import hashlib
from unittest.mock import MagicMock, AsyncMock
import pytest

from src.application.use_cases.verify_applied_fix import VerifyAppliedFixUseCase
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService
from src.domain.entities.code_review import ReviewStatusEnum
from src.domain.entities.fix_suggestion import (
    FixSuggestion,
    FixValidationStatus,
    FixUserDecision,
    FixApplicationStatus,
)
from src.domain.entities.verification import (
    VerificationStatus,
    StaticVerificationResult,
)
from src.infrastructure.filesystem.path_sandbox import PathSandboxService
from src.infrastructure.analysis.static_verification_engine import StaticVerificationEngine
from src.core.errors import ResourceNotFoundError, WorkflowExecutionError


@pytest.fixture
def mock_review_service():
    service = MagicMock(spec=CodeReviewService)
    return service


@pytest.fixture
def mock_repo_service():
    service = MagicMock(spec=RepositoryService)
    return service


@pytest.fixture
def use_case(mock_review_service, mock_repo_service):
    return VerifyAppliedFixUseCase(
        review_service=mock_review_service,
        repository_service=mock_repo_service,
        verification_engine=StaticVerificationEngine(),
        path_sandbox=PathSandboxService(),
    )


@pytest.mark.asyncio
async def test_verify_applied_fix_success(tmp_path, use_case, mock_review_service, mock_repo_service):
    user_id = "user_1"
    review_id = "rev_1"
    repo_id = "repo_1"

    # Setup workspace file
    target_file = tmp_path / "app.py"
    file_bytes = b"def add(a, b):\n    return a + b\n"
    target_file.write_bytes(file_bytes)
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    # Mock review
    mock_review = MagicMock()
    mock_review.id = review_id
    mock_review.user_id = user_id
    mock_review.repository_id = repo_id
    mock_review.status = ReviewStatusEnum.COMPLETED.value
    mock_review.findings_json = [
        {
            "issue": "Missing type annotations",
            "file_path": "app.py",
            "fix_suggestion": {
                "finding_index": 0,
                "file_path": "app.py",
                "original_code": "def add(a, b):",
                "proposed_code": "def add(a: int, b: int) -> int:",
                "explanation": "Add types",
                "diff": "",
                "validation_status": "valid",
                "user_decision": "accepted",
                "application_status": "applied",
                "new_hash": content_hash,
                "language": "python",
            },
        }
    ]

    mock_review_service.get_review.return_value = mock_review
    mock_repo_service.get_repository.return_value = MagicMock(id=repo_id, user_id=user_id)
    mock_review_service.update_finding_verification_result.return_value = {
        "finding_index": 0,
        "static_verification": {"status": "passed"},
    }

    result = await use_case.execute(
        review_id=review_id,
        finding_index=0,
        user_id=user_id,
        workspace_root_override=str(tmp_path),
    )

    assert result["verification"].status == VerificationStatus.PASSED
    assert result["verification"].language == "python"
    mock_review_service.update_finding_verification_result.assert_called_once()


@pytest.mark.asyncio
async def test_verify_applied_fix_is_read_only(tmp_path, use_case, mock_review_service, mock_repo_service):
    user_id = "user_1"
    review_id = "rev_1"
    repo_id = "repo_1"

    target_file = tmp_path / "app.py"
    original_bytes = b"def calculate():\n    return 100\n"
    target_file.write_bytes(original_bytes)
    before_hash = hashlib.sha256(original_bytes).hexdigest()

    mock_review = MagicMock()
    mock_review.id = review_id
    mock_review.user_id = user_id
    mock_review.repository_id = repo_id
    mock_review.status = ReviewStatusEnum.COMPLETED.value
    mock_review.findings_json = [
        {
            "file_path": "app.py",
            "fix_suggestion": {
                "finding_index": 0,
                "file_path": "app.py",
                "original_code": "def calculate():",
                "proposed_code": "def calculate() -> int:",
                "explanation": "types",
                "diff": "",
                "validation_status": "valid",
                "user_decision": "accepted",
                "application_status": "applied",
                "new_hash": before_hash,
                "language": "python",
            },
        }
    ]

    mock_review_service.get_review.return_value = mock_review
    mock_repo_service.get_repository.return_value = MagicMock(id=repo_id, user_id=user_id)
    mock_review_service.update_finding_verification_result.return_value = {}

    await use_case.execute(
        review_id=review_id,
        finding_index=0,
        user_id=user_id,
        workspace_root_override=str(tmp_path),
    )

    after_bytes = target_file.read_bytes()
    after_hash = hashlib.sha256(after_bytes).hexdigest()
    assert before_hash == after_hash
    assert original_bytes == after_bytes


@pytest.mark.asyncio
async def test_verify_detects_source_changed_post_apply(tmp_path, use_case, mock_review_service, mock_repo_service):
    user_id = "user_1"
    review_id = "rev_1"
    repo_id = "repo_1"

    target_file = tmp_path / "app.py"
    # Current content on disk differs from stored new_hash
    target_file.write_text("def modified_later():\n    pass\n", encoding="utf-8")
    stored_apply_hash = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    mock_review = MagicMock()
    mock_review.id = review_id
    mock_review.user_id = user_id
    mock_review.repository_id = repo_id
    mock_review.status = ReviewStatusEnum.COMPLETED.value
    mock_review.findings_json = [
        {
            "file_path": "app.py",
            "fix_suggestion": {
                "finding_index": 0,
                "file_path": "app.py",
                "original_code": "def old():",
                "proposed_code": "def old_fixed():",
                "explanation": "fix",
                "diff": "",
                "validation_status": "valid",
                "user_decision": "accepted",
                "application_status": "applied",
                "new_hash": stored_apply_hash,
                "language": "python",
            },
        }
    ]

    mock_review_service.get_review.return_value = mock_review
    mock_repo_service.get_repository.return_value = MagicMock(id=repo_id, user_id=user_id)
    mock_review_service.update_finding_verification_result.return_value = {}

    result = await use_case.execute(
        review_id=review_id,
        finding_index=0,
        user_id=user_id,
        workspace_root_override=str(tmp_path),
    )

    assert result["verification"].status == VerificationStatus.SOURCE_CHANGED
    assert "modified" in result["verification"].message.lower()


@pytest.mark.asyncio
async def test_verify_rejects_unapplied_fix(use_case, mock_review_service, mock_repo_service):
    user_id = "user_1"
    review_id = "rev_1"
    repo_id = "repo_1"

    mock_review = MagicMock()
    mock_review.id = review_id
    mock_review.user_id = user_id
    mock_review.repository_id = repo_id
    mock_review.status = ReviewStatusEnum.COMPLETED.value
    mock_review.findings_json = [
        {
            "file_path": "app.py",
            "fix_suggestion": {
                "finding_index": 0,
                "file_path": "app.py",
                "original_code": "x = 1",
                "proposed_code": "x = 2",
                "explanation": "change",
                "diff": "",
                "validation_status": "valid",
                "user_decision": "accepted",
                "application_status": "not_applied",  # NOT APPLIED
            },
        }
    ]

    mock_review_service.get_review.return_value = mock_review
    mock_repo_service.get_repository.return_value = MagicMock(id=repo_id, user_id=user_id)

    with pytest.raises(WorkflowExecutionError, match="must be applied before running verification"):
        await use_case.execute(review_id=review_id, finding_index=0, user_id=user_id)


@pytest.mark.asyncio
async def test_verify_enforces_review_ownership(use_case, mock_review_service):
    mock_review_service.get_review.return_value = None  # Access denied / not found

    with pytest.raises(ResourceNotFoundError, match="Review not found"):
        await use_case.execute(review_id="rev_1", finding_index=0, user_id="unauthorized_user")


@pytest.mark.asyncio
async def test_verify_enforces_repository_ownership(use_case, mock_review_service, mock_repo_service):
    mock_review = MagicMock()
    mock_review.id = "rev_1"
    mock_review.user_id = "user_1"
    mock_review.repository_id = "repo_1"
    mock_review.status = ReviewStatusEnum.COMPLETED.value
    mock_review_service.get_review.return_value = mock_review

    mock_repo_service.get_repository.return_value = None  # User does not own repo

    with pytest.raises(ResourceNotFoundError, match="Repository not found"):
        await use_case.execute(review_id="rev_1", finding_index=0, user_id="user_1")


def test_backward_compatibility_fix_suggestion_deserialization():
    # Legacy dictionary without static_verification field
    legacy_data = {
        "finding_index": 0,
        "file_path": "src/main.py",
        "original_code": "def old(): pass",
        "proposed_code": "def new(): pass",
        "explanation": "Rename function",
        "diff": "",
        "confidence_score": 0.95,
        "validation_status": "valid",
        "user_decision": "accepted",
        "application_status": "applied",
        "applied_at": "2026-08-25T12:00:00Z",
    }

    model = FixSuggestion.model_validate(legacy_data)
    assert model.static_verification is None
    assert model.application_status == FixApplicationStatus.APPLIED


@pytest.mark.asyncio
async def test_verify_rejects_rejected_fix(use_case, mock_review_service, mock_repo_service):
    user_id = "user_1"
    review_id = "rev_1"
    repo_id = "repo_1"

    mock_review = MagicMock()
    mock_review.id = review_id
    mock_review.user_id = user_id
    mock_review.repository_id = repo_id
    mock_review.status = ReviewStatusEnum.COMPLETED.value
    mock_review.findings_json = [
        {
            "file_path": "app.py",
            "fix_suggestion": {
                "finding_index": 0,
                "file_path": "app.py",
                "original_code": "x = 1",
                "proposed_code": "x = 2",
                "explanation": "change",
                "diff": "",
                "validation_status": "valid",
                "user_decision": "rejected",
                "application_status": "applied",
            },
        }
    ]

    mock_review_service.get_review.return_value = mock_review
    mock_repo_service.get_repository.return_value = MagicMock(id=repo_id, user_id=user_id)

    with pytest.raises(WorkflowExecutionError, match="Cannot verify a rejected fix suggestion"):
        await use_case.execute(review_id=review_id, finding_index=0, user_id=user_id)


@pytest.mark.asyncio
async def test_verify_finding_index_out_of_range(use_case, mock_review_service, mock_repo_service):
    user_id = "user_1"
    review_id = "rev_1"
    repo_id = "repo_1"

    mock_review = MagicMock()
    mock_review.id = review_id
    mock_review.user_id = user_id
    mock_review.repository_id = repo_id
    mock_review.status = ReviewStatusEnum.COMPLETED.value
    mock_review.findings_json = []  # No findings

    mock_review_service.get_review.return_value = mock_review
    mock_repo_service.get_repository.return_value = MagicMock(id=repo_id, user_id=user_id)

    with pytest.raises(WorkflowExecutionError, match="out of range"):
        await use_case.execute(review_id=review_id, finding_index=5, user_id=user_id)


@pytest.mark.asyncio
async def test_verify_reverification_allowed(tmp_path, use_case, mock_review_service, mock_repo_service):
    user_id = "user_1"
    review_id = "rev_1"
    repo_id = "repo_1"

    target_file = tmp_path / "calc.py"
    code_bytes = b"def multiply(a: int, b: int) -> int:\n    return a * b\n"
    target_file.write_bytes(code_bytes)
    code_hash = hashlib.sha256(code_bytes).hexdigest()

    mock_review = MagicMock()
    mock_review.id = review_id
    mock_review.user_id = user_id
    mock_review.repository_id = repo_id
    mock_review.status = ReviewStatusEnum.COMPLETED.value
    mock_review.findings_json = [
        {
            "file_path": "calc.py",
            "fix_suggestion": {
                "finding_index": 0,
                "file_path": "calc.py",
                "original_code": "def multiply(a, b):",
                "proposed_code": "def multiply(a: int, b: int) -> int:",
                "explanation": "add types",
                "diff": "",
                "validation_status": "valid",
                "user_decision": "accepted",
                "application_status": "applied",
                "new_hash": code_hash,
                "language": "python",
                "static_verification": {
                    "status": "passed",
                    "verified_at": "2026-08-25T10:00:00Z",
                },
            },
        }
    ]

    mock_review_service.get_review.return_value = mock_review
    mock_repo_service.get_repository.return_value = MagicMock(id=repo_id, user_id=user_id)
    mock_review_service.update_finding_verification_result.return_value = {}

    res1 = await use_case.execute(
        review_id=review_id,
        finding_index=0,
        user_id=user_id,
        workspace_root_override=str(tmp_path),
    )
    assert res1["verification"].status == VerificationStatus.PASSED

    # Run verification a second time
    res2 = await use_case.execute(
        review_id=review_id,
        finding_index=0,
        user_id=user_id,
        workspace_root_override=str(tmp_path),
    )
    assert res2["verification"].status == VerificationStatus.PASSED
    assert mock_review_service.update_finding_verification_result.call_count == 2

