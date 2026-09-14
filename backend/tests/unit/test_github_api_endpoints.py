"""
Unit & API Tests for GitHub Integration Endpoints
===================================================
Tests:
- DELETE /api/v1/integrations/github/disconnect
- GET /api/v1/integrations/github/status
- GET /api/v1/integrations/github/repositories (success & 401 expired token)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import get_current_user
from src.interfaces.api.v1.integrations import get_github_integration_service
from src.application.services.github_integration_service import GitHubIntegrationService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_service():
    service = MagicMock(spec=GitHubIntegrationService)
    return service


def _user_override(user_id: str = "test-user-123"):
    def _override():
        return {"sub": user_id, "email": "test@example.com"}
    return _override


class TestGitHubApiEndpoints:
    def test_disconnect_endpoint(self, client, mock_service):
        mock_service.disconnect.return_value = True

        app.dependency_overrides[get_current_user] = _user_override("test-user-123")
        app.dependency_overrides[get_github_integration_service] = lambda: mock_service

        try:
            resp = client.delete("/api/v1/integrations/github/disconnect")
            assert resp.status_code == 200
            data = resp.json()
            assert data["connected"] is False
            assert "disconnected successfully" in data["message"]
            mock_service.disconnect.assert_called_once_with("test-user-123")
        finally:
            app.dependency_overrides.clear()

    def test_status_endpoint(self, client, mock_service):
        mock_service.get_status.return_value = {
            "connected": True,
            "username": "octocat",
            "avatar_url": "https://avatars.github.com/u/583231",
            "connected_at": "2026-09-01T12:00:00Z",
        }

        app.dependency_overrides[get_current_user] = _user_override("test-user-123")
        app.dependency_overrides[get_github_integration_service] = lambda: mock_service

        try:
            resp = client.get("/api/v1/integrations/github/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["connected"] is True
            assert data["username"] == "octocat"
        finally:
            app.dependency_overrides.clear()

    def test_repositories_401_returns_clean_expired_message(self, client, mock_service):
        mock_service.list_user_repositories = AsyncMock(
            side_effect=PermissionError("GitHub connection has expired or token was revoked")
        )

        app.dependency_overrides[get_current_user] = _user_override("test-user-123")
        app.dependency_overrides[get_github_integration_service] = lambda: mock_service

        try:
            resp = client.get("/api/v1/integrations/github/repositories")
            assert resp.status_code == 401
            data = resp.json()
            assert "expired" in data["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_repositories_success(self, client, mock_service):
        mock_service.list_user_repositories = AsyncMock(
            return_value=[
                {
                    "id": "12345",
                    "name": "my-repo",
                    "full_name": "octocat/my-repo",
                    "owner": "octocat",
                    "url": "https://github.com/octocat/my-repo",
                    "clone_url": "https://github.com/octocat/my-repo.git",
                    "is_private": False,
                    "default_branch": "main",
                    "description": "My test repository",
                    "stars": 10,
                    "language": "Python",
                    "updated_at": "2026-09-07T00:00:00Z",
                }
            ]
        )

        app.dependency_overrides[get_current_user] = _user_override("test-user-123")
        app.dependency_overrides[get_github_integration_service] = lambda: mock_service

        try:
            resp = client.get("/api/v1/integrations/github/repositories")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["name"] == "my-repo"
        finally:
            app.dependency_overrides.clear()
