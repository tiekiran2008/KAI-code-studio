"""
Integration tests for Refactoring Analysis API endpoint.
==========================================================
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import get_current_user
from src.interfaces.api.v1.reviews import get_code_review_service


@pytest.fixture
def mock_user():
    return {"id": "user123", "email": "test@example.com"}


@pytest.fixture
def mock_service():
    service = MagicMock()
    review = MagicMock()
    review.id = "rev-123"
    review.repository_id = "repo-456"
    review.user_id = "user123"
    review.status = "completed"
    review.refactoring_findings_json = [
        {
            "refactoring_type": "Extract Method",
            "priority": "high",
            "category": "complexity",
            "file_path": "src/service.py",
            "line_number": 42,
            "explanation": "Function too long, extract helper method",
            "current_problem": "Function process_data exceeds 80 lines",
            "suggested_refactoring": "Extract validation step to helper",
            "before_preview": "def big_func(): ...",
            "after_preview": "def big_func(): helper()\ndef helper(): ...",
            "benefits": ["Better readability", "Easier testing"],
            "risks": ["Slight indirection"],
            "estimated_effort_hours": 1.5,
            "confidence_score": 0.95,
        }
    ]
    review.refactoring_priority = "high"
    review.estimated_refactoring_effort = 1.5
    review.estimated_maintainability_improvement = 20.0
    review.estimated_technical_debt_reduction = 3.0
    review.estimated_complexity_reduction = 25.0
    service.get_review.return_value = review
    return service


def test_get_refactoring_success(mock_user, mock_service):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    response = client.get("/api/v1/reviews/rev-123/refactoring")

    assert response.status_code == 200
    data = response.json()
    assert "refactoring_findings" in data
    assert len(data["refactoring_findings"]) == 1
    assert data["refactoring_findings"][0]["refactoring_type"] == "Extract Method"
    assert data["refactoring_findings"][0]["current_problem"] == "Function process_data exceeds 80 lines"
    assert data["refactoring_priority"] == "high"
    assert data["estimated_refactoring_effort"] == 1.5
    assert data["estimated_maintainability_improvement"] == 20.0
    assert data["estimated_technical_debt_reduction"] == 3.0
    assert data["estimated_complexity_reduction"] == 25.0

    app.dependency_overrides.clear()


def test_get_refactoring_not_found(mock_user):
    mock_service = MagicMock()
    mock_service.get_review.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    response = client.get("/api/v1/reviews/nonexistent/refactoring")

    assert response.status_code == 404
    assert response.json()["detail"] == "Review not found"

    app.dependency_overrides.clear()
