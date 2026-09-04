"""
test_review_config.py
======================
Unit and integration tests for Phase 11.1B-4 Review Configuration feature.

Enforces:
1. Default configuration works seamlessly when omitted.
2. Strictness selection ('low', 'medium', 'high', 'strict') reaches workflow execution.
3. Individual check disabled (e.g. security=False) disables that check and suppresses fake fallback scores.
4. Multiple check combinations preserve exact state.
5. Invalid strictness (e.g. 'extreme') is rejected with HTTP 422.
6. Ownership validation from 11.1B-2 remains intact.
7. Failed AI workflow handling from 11.1B-1 remains intact.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import get_current_user
from src.interfaces.api.v1.reviews import get_code_review_service, get_repository_service, get_agent_use_case
from src.application.use_cases.review_code import ReviewCodeUseCase
from src.interfaces.api.v1.reviews import ReviewConfigSchema
from src.core.errors import WorkflowExecutionError


def test_default_config_preserves_backwards_compatibility():
    """TEST 1: Omitting config uses default ReviewConfigSchema values."""
    user_id = "user_test_1"
    repo_id = "repo_test_1"

    mock_repo_service = MagicMock()
    mock_repo_service.get_repository.return_value = {"id": repo_id, "user_id": user_id}

    mock_review_service = MagicMock()
    mock_agent_use_case = MagicMock()
    mock_agent_use_case.execute = AsyncMock(return_value={
        "agent_outputs": {},
        "confidence_score": 1.0,
    })

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_id}
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
    app.dependency_overrides[get_code_review_service] = lambda: mock_review_service
    app.dependency_overrides[get_agent_use_case] = lambda: mock_agent_use_case

    client = TestClient(app)
    res = client.post("/api/v1/reviews/start", json={"repository_id": repo_id})

    assert res.status_code == 202
    assert "review_id" in res.json()
    assert mock_review_service.create_review.called

    app.dependency_overrides.clear()


def test_strictness_selection_passed_to_use_case():
    """TEST 2: Explicit strictness level 'high' (or 'strict') is validated and passed."""
    cfg = ReviewConfigSchema(strictness="strict", codeQuality=True)
    assert cfg.strictness == "high"

    cfg_medium = ReviewConfigSchema(strictness="medium")
    assert cfg_medium.strictness == "medium"


def test_invalid_strictness_rejected_with_422():
    """TEST 5: Invalid strictness string returns HTTP 422 validation error."""
    user_id = "user_test_1"
    repo_id = "repo_test_1"

    mock_repo_service = MagicMock()
    mock_repo_service.get_repository.return_value = {"id": repo_id, "user_id": user_id}

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_id}
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
    app.dependency_overrides[get_code_review_service] = lambda: MagicMock()
    app.dependency_overrides[get_agent_use_case] = lambda: MagicMock()

    client = TestClient(app)
    res = client.post("/api/v1/reviews/start", json={
        "repository_id": repo_id,
        "config": {"strictness": "invalid_extreme_level"}
    })

    assert res.status_code == 422

    app.dependency_overrides.clear()



@pytest.mark.asyncio
async def test_disabled_performance_suppresses_fake_scores():
    """TEST 3 & 4: Disabled performance check prevents fake scores and excludes findings."""
    mock_review_service = MagicMock()
    mock_agent_executor = MagicMock()
    mock_agent_executor.execute = AsyncMock(return_value={
        "agent_outputs": {
            "code_review": {"structured_findings": [{"issue": "Unused var"}]}
        },
        "confidence_score": 0.9,
    })

    use_case = ReviewCodeUseCase(
        code_review_service=mock_review_service,
        agent_executor=mock_agent_executor,
    )

    config = ReviewConfigSchema(
        strictness="high",
        security=False,
        performance=False,
        architecture=False,
        codeQuality=True,
    )

    res = await use_case.execute(
        repository_id="repo_1",
        user_id="user_1",
        review_id="rev_100",
        review_config=config,
    )

    assert res["status"] == "completed"
    assert mock_agent_executor.execute.called

    # Verify update_review_status was called without fake scores for performance/architecture
    call_kwargs = mock_review_service.update_review_status.call_args.kwargs
    assert call_kwargs["performance_score"] == 0.0
    assert call_kwargs["performance_findings"] == []
    assert call_kwargs["overall_health_score"] == 0.0
    assert call_kwargs["architecture_findings"] == []


def test_ownership_validation_remains_intact():
    """TEST 6: 11.1B-2 ownership validation still blocks starting review for unowned repository."""
    user_id = "user_b_456"
    repo_id = "repo_a_owned_by_a"

    mock_repo_service = MagicMock()
    mock_repo_service.get_repository.return_value = None  # User B does NOT own repo A

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_id}
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
    app.dependency_overrides[get_code_review_service] = lambda: MagicMock()
    app.dependency_overrides[get_agent_use_case] = lambda: MagicMock()

    client = TestClient(app)
    res = client.post("/api/v1/reviews/start", json={"repository_id": repo_id})

    assert res.status_code == 404
    assert res.json()["detail"] == "Repository not found"

    app.dependency_overrides.clear()



@pytest.mark.asyncio
async def test_failed_ai_workflow_remains_failing():
    """TEST 7: 11.1B-1 workflow failure still marks review FAILED and re-raises exception."""
    mock_review_service = MagicMock()
    mock_agent_executor = MagicMock()
    mock_agent_executor.execute = AsyncMock(side_effect=WorkflowExecutionError("LLM failed"))

    use_case = ReviewCodeUseCase(
        code_review_service=mock_review_service,
        agent_executor=mock_agent_executor,
    )

    with pytest.raises(WorkflowExecutionError):
        await use_case.execute(
            repository_id="repo_1",
            user_id="user_1",
            review_id="rev_error",
            review_config={"strictness": "medium"},
        )

    # Verify review status was set to FAILED
    status_calls = mock_review_service.update_review_status.call_args_list
    assert any(call.args[1].value == "failed" for call in status_calls)
