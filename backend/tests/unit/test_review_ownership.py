"""
test_review_ownership.py
========================
Tests for review ownership and cross-tenant access control (Phase 11.1B-2).

Enforces:
1. User A can access User A's review (200 OK).
2. User B CANNOT access User A's review (404 Not Found).
3. Unauthenticated requests are rejected (401 Unauthorized).
4. Invalid/nonexistent review IDs return 404.
5. User B CANNOT start a review for User A's repository (404 Not Found).
6. User A CAN start a review for User A's repository (202 Accepted).
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.core.config import settings
from src.interfaces.api.dependencies import (
    get_current_user,
    get_agent_use_case,
    get_repository_service,
)
from src.interfaces.api.v1.reviews import get_code_review_service
from src.infrastructure.persistence.code_review_models import DBCodeReview


def _create_db_review(review_id: str, user_id: str, repo_id: str = "repo_123") -> DBCodeReview:
    return DBCodeReview(
        id=review_id,
        user_id=user_id,
        repository_id=repo_id,
        status="completed",
        findings_json=[],
        performance_findings_json=[],
        confidence_score=1.0,
        duration_ms=500,
        performance_score=95.0,
        performance_recommendations_json=[],
        estimated_cpu_savings=10.0,
        estimated_memory_savings=20.0,
        estimated_latency_improvement=15.0,
        refactoring_findings_json=[],
        refactoring_priority="low",
        estimated_refactoring_effort=0.0,
        estimated_maintainability_improvement=0.0,
        estimated_technical_debt_reduction=0.0,
        estimated_complexity_reduction=0.0,
        architecture_findings_json=[],
        overall_health_score=90.0,
        architecture_score=90.0,
        maintainability_score=90.0,
        technical_debt_score=90.0,
        complexity_score=90.0,
        documentation_score=90.0,
        modularity_score=90.0,
        testability_score=90.0,
        dependency_analysis_json={},
    )


@pytest.fixture
def mock_agent_executor():
    executor = MagicMock()
    executor.execute = AsyncMock(return_value={
        "answer": "Mocked review",
        "agent_outputs": {},
        "confidence_score": 0.9,
    })
    executor.graph = MagicMock()
    return executor


def test_user_a_requests_user_a_review():
    """TEST 1: User A requests User A review -> 200"""
    user_a_id = "user_a_123"
    review_id = "review_a_999"

    db_review = _create_db_review(review_id, user_a_id)

    mock_service = MagicMock()
    def get_review_side_effect(rid, user_id=None):
        if rid == review_id and user_id == user_a_id:
            return db_review
        return None

    mock_service.get_review.side_effect = get_review_side_effect

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    res = client.get(f"/api/v1/reviews/{review_id}")

    assert res.status_code == 200
    assert res.json()["id"] == review_id
    app.dependency_overrides.clear()


def test_user_b_requests_user_a_review():
    """TEST 2: User B requests User A review -> 404 (not 200, no data exposure)"""
    user_a_id = "user_a_123"
    user_b_id = "user_b_456"
    review_id = "review_a_999"

    db_review = _create_db_review(review_id, user_a_id)

    mock_service = MagicMock()
    def get_review_side_effect(rid, user_id=None):
        if rid == review_id and user_id == user_a_id:
            return db_review
        return None

    mock_service.get_review.side_effect = get_review_side_effect

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_b_id}
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    res = client.get(f"/api/v1/reviews/{review_id}")

    assert res.status_code == 404
    assert res.json()["detail"] == "Review not found"
    app.dependency_overrides.clear()


def test_unauthenticated_request_rejected():
    """TEST 3: Unauthenticated request -> 401"""
    app.dependency_overrides.clear()
    original_bypass = settings.DEV_AUTH_BYPASS
    settings.DEV_AUTH_BYPASS = False
    try:
        client = TestClient(app)
        res = client.get("/api/v1/reviews/review_a_999")
        assert res.status_code == 401
    finally:
        settings.DEV_AUTH_BYPASS = original_bypass


def test_nonexistent_review_id():
    """TEST 4: Invalid/nonexistent review ID -> 404"""
    mock_service = MagicMock()
    mock_service.get_review.return_value = None

    app.dependency_overrides[get_current_user] = lambda: {"sub": "user_a_123"}
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    res = client.get("/api/v1/reviews/nonexistent_id_000")

    assert res.status_code == 404
    assert res.json()["detail"] == "Review not found"
    app.dependency_overrides.clear()


def test_user_b_attempts_start_review_for_user_a_repository(mock_agent_executor):
    """TEST 5: User B attempts to start review for User A's repository -> 404 (rejected)"""
    user_a_id = "user_a_123"
    user_b_id = "user_b_456"
    repo_a_id = "repo_owned_by_user_a"

    mock_repo_service = MagicMock()
    def get_repo_side_effect(uid, rid):
        if uid == user_a_id and rid == repo_a_id:
            repo = MagicMock()
            repo.id = repo_a_id
            repo.user_id = user_a_id
            return repo
        return None

    mock_repo_service.get_repository.side_effect = get_repo_side_effect

    mock_code_review_service = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_b_id}
    app.dependency_overrides[get_code_review_service] = lambda: mock_code_review_service
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
    app.dependency_overrides[get_agent_use_case] = lambda: mock_agent_executor

    client = TestClient(app)
    res = client.post(
        "/api/v1/reviews/start",
        json={"repository_id": repo_a_id},
    )

    assert res.status_code == 404
    assert res.json()["detail"] == "Repository not found"
    mock_code_review_service.create_review.assert_not_called()

    app.dependency_overrides.clear()


def test_user_a_starts_review_for_own_repository(mock_agent_executor):
    """TEST 6: Correct owner starts review -> 202 Accepted"""
    user_a_id = "user_a_123"
    repo_a_id = "repo_owned_by_user_a"

    mock_repo_service = MagicMock()
    repo = MagicMock()
    repo.id = repo_a_id
    repo.user_id = user_a_id
    repo.indexing_status = "indexed"
    mock_repo_service.get_repository.return_value = repo

    mock_code_review_service = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
    app.dependency_overrides[get_code_review_service] = lambda: mock_code_review_service
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
    app.dependency_overrides[get_agent_use_case] = lambda: mock_agent_executor

    client = TestClient(app)
    res = client.post(
        "/api/v1/reviews/start",
        json={"repository_id": repo_a_id},
    )

    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "pending"
    assert "review_id" in data
    mock_code_review_service.create_review.assert_called_once()

    app.dependency_overrides.clear()


def test_unindexed_repository_rejects_review(mock_agent_executor):
    """TEST 6b: Repository indexing status != indexed -> 400 Bad Request"""
    user_a_id = "user_a_123"
    repo_a_id = "repo_owned_by_user_a"

    mock_repo_service = MagicMock()
    repo = MagicMock()
    repo.id = repo_a_id
    repo.user_id = user_a_id
    repo.indexing_status = "failed"
    mock_repo_service.get_repository.return_value = repo

    mock_code_review_service = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
    app.dependency_overrides[get_code_review_service] = lambda: mock_code_review_service
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
    app.dependency_overrides[get_agent_use_case] = lambda: mock_agent_executor

    client = TestClient(app)
    res = client.post(
        "/api/v1/reviews/start",
        json={"repository_id": repo_a_id},
    )

    assert res.status_code == 400
    assert "Repository indexing must complete before code review can start." in res.json()["detail"]
    mock_code_review_service.create_review.assert_not_called()

    app.dependency_overrides.clear()


def test_cross_user_access_blocked_for_all_sub_endpoints():
    """Verify performance, refactoring, architecture, and history sub-endpoints enforce ownership."""
    user_a_id = "user_a_123"
    user_b_id = "user_b_456"
    review_id = "review_a_999"
    repo_a_id = "repo_a_1"

    db_review = _create_db_review(review_id, user_a_id, repo_a_id)

    mock_service = MagicMock()
    mock_service.get_review.side_effect = lambda rid, user_id=None: db_review if (rid == review_id and user_id == user_a_id) else None
    mock_service.get_repository_reviews.side_effect = lambda rid, user_id=None, skip=0, limit=50: [db_review] if (rid == repo_a_id and user_id == user_a_id) else []

    mock_repo_service = MagicMock()
    mock_repo_service.get_repository.side_effect = lambda uid, rid: MagicMock() if (uid == user_a_id and rid == repo_a_id) else None

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_b_id}
    app.dependency_overrides[get_code_review_service] = lambda: mock_service
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service

    client = TestClient(app)

    # 1. Performance endpoint
    res = client.get(f"/api/v1/reviews/{review_id}/performance")
    assert res.status_code == 404

    # 2. Refactoring endpoint
    res = client.get(f"/api/v1/reviews/{review_id}/refactoring")
    assert res.status_code == 404

    # 3. Architecture endpoint
    res = client.get(f"/api/v1/reviews/{review_id}/architecture")
    assert res.status_code == 404

    # 4. History endpoint
    res = client.get(f"/api/v1/reviews/history/{repo_a_id}")
    assert res.status_code == 404

    app.dependency_overrides.clear()
