import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import get_current_user, get_agent_use_case
from src.interfaces.api.v1.reviews import get_code_review_service


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer testtoken"}


@pytest.fixture
def dummy_review():
    review = MagicMock()
    review.id = "rev_123"
    review.repository_id = "repo_123"
    review.status = "completed"
    review.performance_score = 95.0
    review.performance_findings_json = []
    review.performance_recommendations_json = []
    review.estimated_cpu_savings = 10.0
    review.estimated_memory_savings = 20.0
    review.estimated_latency_improvement = 15.0
    return review


@pytest.fixture
def mock_service(dummy_review):
    service = MagicMock()
    service.get_review.return_value = dummy_review
    service.create_review.return_value = dummy_review
    service.update_review_status.return_value = dummy_review
    return service


@pytest.fixture
def mock_agent_executor():
    """Stub ExecuteAgentWorkflowUseCase — never calls a real LLM."""
    executor = MagicMock()
    executor.execute = AsyncMock(return_value={
        "answer": "Mocked review",
        "agent_outputs": {},
        "confidence_score": 0.9,
        "citations": [],
        "groundedness_ratio": 0.9,
        "execution_trace": [],
        "latency_ms": 100.0,
    })
    # The graph attribute is accessed during ReviewCodeUseCase init
    executor.graph = MagicMock()
    return executor


@pytest.fixture
def mock_repo_service():
    service = MagicMock()
    repo = MagicMock()
    repo.id = "repo_123"
    repo.user_id = "test_user_id"
    repo.indexing_status = "indexed"
    service.get_repository.return_value = repo
    return service


@pytest.fixture
def client(mock_service, mock_agent_executor, mock_repo_service):
    app.dependency_overrides[get_current_user] = lambda: {"sub": "test_user_id"}
    app.dependency_overrides[get_code_review_service] = lambda: mock_service
    app.dependency_overrides[get_agent_use_case] = lambda: mock_agent_executor
    from src.interfaces.api.dependencies import get_repository_service
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def setup_dummy_review(dummy_review):
    return dummy_review


def test_start_review(client: TestClient, auth_headers: dict):
    response = client.post(
        "/api/v1/reviews/start",
        json={"repository_id": "repo_123", "files": []},
        headers=auth_headers,
    )
    assert response.status_code == 202
    data = response.json()
    assert "review_id" in data
    assert data["status"] == "pending"


def test_get_review(client: TestClient, auth_headers: dict, setup_dummy_review):
    review_id = setup_dummy_review.id
    response = client.get(f"/api/v1/reviews/{review_id}", headers=auth_headers)
    assert response.status_code == 200


def test_get_performance(client: TestClient, auth_headers: dict, setup_dummy_review):
    review_id = setup_dummy_review.id
    response = client.get(f"/api/v1/reviews/{review_id}/performance", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "performance_score" in data
    assert "performance_findings" in data
    assert "performance_recommendations" in data
