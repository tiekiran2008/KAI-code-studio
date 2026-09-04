"""
test_review_history.py
======================
Unit and integration tests for Phase 11.1B-3 Review History feature.

Enforces:
1. Owner can list their own code reviews (GET /api/v1/reviews).
2. Another user (User B) does NOT receive User A's reviews in their history list.
3. Unauthenticated requests are rejected (401 Unauthorized).
4. Empty history returns 200 OK with empty array [].
5. Query parameter filters (repository_id, status) work correctly.
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.core.config import settings
from src.interfaces.api.dependencies import get_current_user
from src.interfaces.api.v1.reviews import get_code_review_service
from src.infrastructure.persistence.code_review_models import DBCodeReview


def _create_db_review(review_id: str, user_id: str, repo_id: str = "repo_100", status: str = "completed") -> DBCodeReview:
    return DBCodeReview(
        id=review_id,
        user_id=user_id,
        repository_id=repo_id,
        status=status,
        findings_json=[],
        performance_findings_json=[],
        confidence_score=1.0,
        duration_ms=450,
        performance_score=92.0,
        performance_recommendations_json=[],
        estimated_cpu_savings=5.0,
        estimated_memory_savings=10.0,
        estimated_latency_improvement=8.0,
        refactoring_findings_json=[],
        refactoring_priority="low",
        estimated_refactoring_effort=0.0,
        estimated_maintainability_improvement=0.0,
        estimated_technical_debt_reduction=0.0,
        estimated_complexity_reduction=0.0,
        architecture_findings_json=[],
        overall_health_score=88.0,
        architecture_score=88.0,
        maintainability_score=88.0,
        technical_debt_score=88.0,
        complexity_score=88.0,
        documentation_score=88.0,
        modularity_score=88.0,
        testability_score=88.0,
        dependency_analysis_json={},
    )


def test_owner_lists_user_reviews():
    """TEST 1: Owner lists their own code reviews -> 200 OK with review array."""
    user_a_id = "user_a_123"
    review1 = _create_db_review("rev_1", user_a_id, "repo_1", "completed")
    review2 = _create_db_review("rev_2", user_a_id, "repo_2", "pending")

    mock_service = MagicMock()
    def list_user_reviews_side_effect(user_id, repository_id=None, status=None, skip=0, limit=50):
        if user_id == user_a_id:
            res = [review1, review2]
            if repository_id:
                res = [r for r in res if r.repository_id == repository_id]
            if status:
                res = [r for r in res if r.status == status]
            return res
        return []

    mock_service.list_user_reviews.side_effect = list_user_reviews_side_effect

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_a_id}
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    res = client.get("/api/v1/reviews")

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["id"] == "rev_1"
    assert data[1]["id"] == "rev_2"

    app.dependency_overrides.clear()


def test_cross_user_isolation_on_review_list():
    """TEST 2: User B calling GET /api/v1/reviews receives 0 of User A's reviews."""
    user_a_id = "user_a_123"
    user_b_id = "user_b_456"

    review_a = _create_db_review("rev_a", user_a_id)

    mock_service = MagicMock()
    def list_user_reviews_side_effect(user_id, repository_id=None, status=None, skip=0, limit=50):
        if user_id == user_a_id:
            return [review_a]
        return []  # User B has 0 reviews

    mock_service.list_user_reviews.side_effect = list_user_reviews_side_effect

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_b_id}
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    res = client.get("/api/v1/reviews")

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 0
    assert data == []

    app.dependency_overrides.clear()


def test_unauthenticated_review_list_rejected():
    """TEST 3: Unauthenticated GET /api/v1/reviews -> 401 Unauthorized."""
    app.dependency_overrides.clear()
    original_bypass = settings.DEV_AUTH_BYPASS
    settings.DEV_AUTH_BYPASS = False

    try:
        client = TestClient(app)
        res = client.get("/api/v1/reviews")
        assert res.status_code == 401
    finally:
        settings.DEV_AUTH_BYPASS = original_bypass


def test_empty_review_history():
    """TEST 4: Empty history returns 200 OK with empty array []."""
    mock_service = MagicMock()
    mock_service.list_user_reviews.return_value = []

    app.dependency_overrides[get_current_user] = lambda: {"sub": "user_new"}
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    res = client.get("/api/v1/reviews")

    assert res.status_code == 200
    assert res.json() == []

    app.dependency_overrides.clear()


def test_review_history_filtering_parameters():
    """TEST 5: Query parameter filtering by repository_id and status works correctly."""
    user_id = "user_a_123"
    review1 = _create_db_review("rev_1", user_id, "repo_100", "completed")

    mock_service = MagicMock()
    def list_user_reviews_side_effect(user_id, repository_id=None, status=None, skip=0, limit=50):
        if repository_id == "repo_100" and status == "completed":
            return [review1]
        return []

    mock_service.list_user_reviews.side_effect = list_user_reviews_side_effect

    app.dependency_overrides[get_current_user] = lambda: {"sub": user_id}
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    res = client.get("/api/v1/reviews?repository_id=repo_100&status=completed")

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == "rev_1"

    app.dependency_overrides.clear()
