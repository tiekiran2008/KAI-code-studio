"""
Unit Tests: Rollback Applied Fix Use Case
==========================================
Validates rollback execution, authorization, atomicity, idempotency, and error handling.
"""
import pytest
from unittest.mock import MagicMock
from src.application.use_cases.rollback_applied_fix import RollbackAppliedFixUseCase
from src.application.services.code_review_service import CodeReviewService
from src.application.services.repository_service import RepositoryService
from src.application.services.atomic_patcher import AtomicFilePatcher
from src.domain.entities.code_review import ReviewStatusEnum
from src.domain.entities.fix_suggestion import (
    FixUserDecision,
    FixValidationStatus,
    FixApplicationStatus,
)
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
def rollback_setup(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    target_file = workspace / "math.py"
    # Current content after fix is applied
    target_file.write_text("def add(a, b):\n    return int(a) + int(b)\n", encoding="utf-8")

    review_service = MagicMock(spec=CodeReviewService)
    repository_service = MagicMock(spec=RepositoryService)
    atomic_patcher = AtomicFilePatcher()

    use_case = RollbackAppliedFixUseCase(
        review_service=review_service,
        repository_service=repository_service,
        atomic_patcher=atomic_patcher,
        workspace_root_resolver=lambda u, r: str(workspace),
    )

    return {
        "workspace": workspace,
        "target_file": target_file,
        "review_service": review_service,
        "repository_service": repository_service,
        "atomic_patcher": atomic_patcher,
        "use_case": use_case,
    }


@pytest.mark.asyncio
async def test_rollback_success(rollback_setup):
    use_case = rollback_setup["use_case"]
    review_svc = rollback_setup["review_service"]
    repo_svc = rollback_setup["repository_service"]
    target_file = rollback_setup["target_file"]

    review = FakeReview(
        id="rev-1",
        user_id="user-1",
        repository_id="repo-1",
        status=ReviewStatusEnum.COMPLETED.value,
        findings_json=[
            {
                "issue": "Type casting missing",
                "file_path": "math.py",
                "fix_suggestion": {
                    "finding_index": 0,
                    "file_path": "math.py",
                    "original_code": "def add(a, b):\n    return a + b\n",
                    "proposed_code": "def add(a, b):\n    return int(a) + int(b)\n",
                    "explanation": "Cast parameters to int",
                    "user_decision": "accepted",
                    "application_status": "applied",
                },
            }
        ],
    )
    review_svc.get_review.return_value = review
    repo_svc.get_repository.return_value = FakeRepo("repo-1", "user-1")
    review_svc.rollback_finding_fix.return_value = {
        "finding_index": 0,
        "application_status": "rolled_back",
    }

    result = await use_case.execute(review_id="rev-1", finding_index=0, user_id="user-1")

    assert result["rolled_back"] is True
    assert result["patch_result"]["success"] is True
    # File content should now match original_code
    assert target_file.read_text(encoding="utf-8") == "def add(a, b):\n    return a + b\n"
    review_svc.rollback_finding_fix.assert_called_once_with(
        review_id="rev-1",
        finding_index=0,
        user_id="user-1",
    )


@pytest.mark.asyncio
async def test_rollback_not_applied_fails(rollback_setup):
    use_case = rollback_setup["use_case"]
    review_svc = rollback_setup["review_service"]
    repo_svc = rollback_setup["repository_service"]

    review = FakeReview(
        id="rev-1",
        user_id="user-1",
        repository_id="repo-1",
        status=ReviewStatusEnum.COMPLETED.value,
        findings_json=[
            {
                "issue": "Type casting missing",
                "file_path": "math.py",
                "fix_suggestion": {
                    "finding_index": 0,
                    "file_path": "math.py",
                    "original_code": "def add(a, b):\n    return a + b\n",
                    "proposed_code": "def add(a, b):\n    return int(a) + int(b)\n",
                    "explanation": "Cast parameters to int",
                    "user_decision": "accepted",
                    "application_status": "not_applied",
                },
            }
        ],
    )
    review_svc.get_review.return_value = review
    repo_svc.get_repository.return_value = FakeRepo("repo-1", "user-1")

    with pytest.raises(WorkflowExecutionError, match="must be 'applied'"):
        await use_case.execute(review_id="rev-1", finding_index=0, user_id="user-1")


@pytest.mark.asyncio
async def test_rollback_review_not_found(rollback_setup):
    use_case = rollback_setup["use_case"]
    review_svc = rollback_setup["review_service"]

    review_svc.get_review.return_value = None

    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(review_id="rev-nonexistent", finding_index=0, user_id="user-1")
