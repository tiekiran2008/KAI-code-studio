"""
Integration tests for Architecture & Code Quality API endpoint (Phase 11.5)
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
    review.architecture_findings_json = [
        {
            "category": "clean_architecture",
            "severity": "high",
            "priority": "high",
            "file_path": "src/domain/user.py",
            "line_number": 10,
            "explanation": "Domain entity directly imports ORM model.",
            "root_cause": "Coupling domain to persistence.",
            "business_impact": "High testing friction.",
            "recommendation": "Decouple domain model.",
            "estimated_effort_hours": 2.5,
            "confidence_score": 0.9,
        }
    ]
    review.overall_health_score = 86.0
    review.architecture_score = 88.0
    review.maintainability_score = 82.0
    review.technical_debt_score = 80.0
    review.complexity_score = 85.0
    review.documentation_score = 84.0
    review.modularity_score = 87.0
    review.testability_score = 89.0
    review.dependency_analysis_json = {
        "layer_violations": [],
        "hotspot_files": [],
    }
    service.get_review.return_value = review
    return service


def test_get_architecture_success(mock_user, mock_service):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    response = client.get("/api/v1/reviews/rev-123/architecture")

    assert response.status_code == 200
    data = response.json()
    assert "architecture_findings" in data
    assert len(data["architecture_findings"]) == 1
    assert data["overall_health_score"] == 86.0
    assert data["architecture_score"] == 88.0
    assert data["maintainability_score"] == 82.0
    assert data["technical_debt_score"] == 80.0
    assert data["complexity_score"] == 85.0
    assert data["documentation_score"] == 84.0
    assert data["modularity_score"] == 87.0
    assert data["testability_score"] == 89.0

    app.dependency_overrides.clear()


def test_get_architecture_not_found(mock_user):
    mock_service = MagicMock()
    mock_service.get_review.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_code_review_service] = lambda: mock_service

    client = TestClient(app)
    response = client.get("/api/v1/reviews/nonexistent/architecture")

    assert response.status_code == 404
    assert response.json()["detail"] == "Review not found"

    app.dependency_overrides.clear()
