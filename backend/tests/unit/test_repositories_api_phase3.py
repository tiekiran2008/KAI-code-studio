from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import (
    get_current_user,
    get_repository_service,
    get_repository_ingestion_service,
)
from src.domain.entities.repository import (
    Repository,
    RepositoryProvider,
    IndexingStatus,
    RepositoryIndexStatus,
)
from src.application.services.repository_ingestion_service import RepositoryIndexProgress


@pytest.fixture
def mock_user():
    return {"sub": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def mock_repo_service():
    service = MagicMock()
    fake_repo = Repository(
        id="repo-123",
        user_id="test-user-123",
        url="https://github.com/example/test-repo",
        provider=RepositoryProvider.GITHUB,
        name="test-repo",
        description="Test Repository",
        owner="example",
        default_branch="main",
        current_branch="main",
        branches=["main"],
        indexing_status=IndexingStatus.PENDING,
        chunks_count=0,
        created_at="2026-09-04T10:00:00Z",
    )
    service.import_repository.return_value = fake_repo
    service.get_repository.return_value = fake_repo
    return service


@pytest.fixture
def mock_ingestion_service():
    service = MagicMock()
    prog = RepositoryIndexProgress(
        repository_id="repo-123",
        status="indexing",
        stage="chunking",
        progress=45.0,
        files_discovered=10,
        files_processed=5,
        chunks_created=25,
    )
    service.get_progress.return_value = prog
    return service


def test_import_repository_api_launches_background_indexing(mock_user, mock_repo_service, mock_ingestion_service):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
    app.dependency_overrides[get_repository_ingestion_service] = lambda: mock_ingestion_service

    client = TestClient(app)
    response = client.post(
        "/api/v1/repositories/import",
        json={
            "url": "https://github.com/example/test-repo",
            "provider": "github",
            "name": "test-repo",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "repo-123"
    assert data["name"] == "test-repo"

    app.dependency_overrides.clear()


def test_get_index_status_api(mock_user, mock_repo_service, mock_ingestion_service):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
    app.dependency_overrides[get_repository_ingestion_service] = lambda: mock_ingestion_service

    client = TestClient(app)
    response = client.get("/api/v1/repositories/repo-123/index-status")

    assert response.status_code == 200
    data = response.json()
    assert data["repository_id"] == "repo-123"
    assert data["status"] == "indexing"
    assert data["progress"] == 45.0
    assert data["files_discovered"] == 10
    assert data["chunks_created"] == 25

    app.dependency_overrides.clear()


def test_reindex_repository_api(mock_user, mock_repo_service, mock_ingestion_service):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service
    app.dependency_overrides[get_repository_ingestion_service] = lambda: mock_ingestion_service

    client = TestClient(app)
    response = client.post("/api/v1/repositories/repo-123/reindex")

    assert response.status_code == 200
    data = response.json()
    assert data["repository_id"] == "repo-123"
    assert data["status"] == "indexing"

    app.dependency_overrides.clear()
