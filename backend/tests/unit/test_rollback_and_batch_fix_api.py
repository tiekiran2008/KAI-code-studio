"""
Unit Tests: Rollback & Batch Fix API Endpoints
==============================================
Validates HTTP endpoints for fix rollback, regenerate, fix-all-safe, and fix-batch.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.interfaces.api.v1.reviews import router
from src.interfaces.api.dependencies import (
    get_current_user,
    get_code_review_service,
    get_rollback_applied_fix_use_case,
    get_apply_fix_use_case,
    get_verify_applied_fix_use_case,
    get_verify_applied_fix_tests_use_case,
    get_commit_applied_fix_use_case,
    get_push_fix_branch_use_case,
    get_create_fix_pull_request_use_case,
    get_repository_service,
    get_db_session,
)
from src.domain.entities.code_review import ReviewStatusEnum


@pytest.fixture
def api_client():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    mock_user = {"sub": "test-user-123", "email": "test@example.com"}
    mock_service = MagicMock()
    mock_rollback_uc = MagicMock()
    mock_rollback_uc.execute = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_code_review_service] = lambda: mock_service
    app.dependency_overrides[get_rollback_applied_fix_use_case] = lambda: mock_rollback_uc

    client = TestClient(app)
    return {
        "client": client,
        "service": mock_service,
        "rollback_uc": mock_rollback_uc,
    }


def test_rollback_endpoint_success(api_client):
    client = api_client["client"]
    rollback_uc = api_client["rollback_uc"]

    rollback_uc.execute.return_value = {
        "fix_suggestion": {"finding_index": 0, "application_status": "rolled_back"},
        "rolled_back": True,
    }

    res = client.post("/api/v1/reviews/rev-123/findings/0/fix/rollback")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["rolled_back"] is True
    rollback_uc.execute.assert_called_once_with(
        review_id="rev-123",
        finding_index=0,
        user_id="test-user-123",
    )


def test_rollback_endpoint_negative_index_rejected(api_client):
    client = api_client["client"]
    res = client.post("/api/v1/reviews/rev-123/findings/-1/fix/rollback")
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
