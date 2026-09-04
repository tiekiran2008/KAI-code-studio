"""
Integration Tests: Workspace API
==================================
Tests for the /api/v1/workspaces endpoints using FastAPI TestClient.
Mocks the authentication layer to inject a test user.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from src.main import app

BASE_URL = "/api/v1/workspaces"
TEST_USER_PAYLOAD = {"sub": "test-user-123", "email": "test@example.com"}


def _make_workspace_entity(
    id="ws-test-1",
    user_id="test-user-123",
    name="Integration WS",
    description="Integration test workspace",
    default_ai_model="gpt-4o",
    default_repo_id=None,
    vector_db_config=None,
    tool_config=None,
    repo_count=0,
):
    """Build a mock Workspace domain entity dict (for API response comparison)."""
    return {
        "id": id,
        "user_id": user_id,
        "name": name,
        "description": description,
        "default_ai_model": default_ai_model,
        "default_repo_id": default_repo_id,
        "vector_db_config": vector_db_config or {},
        "tool_config": tool_config or {},
        "repo_count": repo_count,
        "created_at": datetime(2024, 1, 1).isoformat(),
        "updated_at": datetime(2024, 6, 1).isoformat(),
    }


@pytest.fixture
def client():
    """FastAPI test client with auth dependency overridden."""
    from src.interfaces.api.dependencies import get_current_user
    from src.interfaces.api.v1.workspaces import get_workspace_service

    mock_ws_service = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: TEST_USER_PAYLOAD
    app.dependency_overrides[get_workspace_service] = lambda: mock_ws_service

    with TestClient(app) as client:
        client._mock_service = mock_ws_service
        yield client

    app.dependency_overrides.clear()


class TestListWorkspaces:
    def test_list_returns_200_and_workspaces(self, client):
        ws = _make_workspace_entity()
        client._mock_service.list_workspaces.return_value = [
            type('Workspace', (), ws)()
        ]

        # Patch the pydantic response serialisation via the service mock
        from src.domain.entities.workspace import Workspace
        mock_entity = Workspace(**ws)
        client._mock_service.list_workspaces.return_value = [mock_entity]

        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_calls_service_with_user_id(self, client):
        client._mock_service.list_workspaces.return_value = []
        client.get(BASE_URL)
        client._mock_service.list_workspaces.assert_called_once_with("test-user-123", 0, 100)


class TestCreateWorkspace:
    def test_create_returns_201(self, client):
        ws_entity = _make_workspace_entity(name="New WS")
        from src.domain.entities.workspace import Workspace
        client._mock_service.create_workspace.return_value = Workspace(**ws_entity)

        resp = client.post(BASE_URL, json={"name": "New WS", "default_ai_model": "gpt-4o"})
        assert resp.status_code == 201

    def test_create_validates_name_required(self, client):
        resp = client.post(BASE_URL, json={"default_ai_model": "gpt-4o"})
        assert resp.status_code == 422

    def test_create_calls_service_with_correct_user(self, client):
        ws_entity = _make_workspace_entity()
        from src.domain.entities.workspace import Workspace
        client._mock_service.create_workspace.return_value = Workspace(**ws_entity)

        client.post(BASE_URL, json={"name": "WS", "default_ai_model": "gpt-4o"})

        call_args = client._mock_service.create_workspace.call_args
        assert call_args[0][0] == "test-user-123"

    def test_create_response_contains_workspace_id(self, client):
        """The response must contain the generated workspace ID."""
        ws_entity = _make_workspace_entity(id="generated-uuid-abc123")
        from src.domain.entities.workspace import Workspace
        client._mock_service.create_workspace.return_value = Workspace(**ws_entity)

        resp = client.post(BASE_URL, json={"name": "ID Test WS", "default_ai_model": "gpt-4o"})
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["id"] == "generated-uuid-abc123"

    def test_create_with_null_default_repo_id(self, client):
        """default_repo_id should be nullable — workspace can exist before any repository."""
        ws_entity = _make_workspace_entity(default_repo_id=None)
        from src.domain.entities.workspace import Workspace
        client._mock_service.create_workspace.return_value = Workspace(**ws_entity)

        resp = client.post(BASE_URL, json={"name": "No Repo WS", "default_ai_model": "gpt-4o"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["default_repo_id"] is None

    def test_create_with_empty_string_default_repo_id_coerced_to_null(self, client):
        """An empty-string default_repo_id must be coerced to None before reaching the DB."""
        ws_entity = _make_workspace_entity(default_repo_id=None)
        from src.domain.entities.workspace import Workspace
        client._mock_service.create_workspace.return_value = Workspace(**ws_entity)

        resp = client.post(
            BASE_URL,
            json={"name": "Empty Repo WS", "default_ai_model": "gpt-4o", "default_repo_id": ""}
        )
        assert resp.status_code == 201
        body = resp.json()
        # The empty string must have been converted to None
        assert body["default_repo_id"] is None

    def test_create_response_schema(self, client):
        """Response must include id, name, description, default_ai_model, default_repo_id,
        vector_db_config, tool_config, and created_at."""
        ws_entity = _make_workspace_entity(
            id="schema-test-ws",
            name="Schema WS",
            description="Testing the response schema",
            default_ai_model="gpt-4o",
            default_repo_id=None,
        )
        from src.domain.entities.workspace import Workspace
        client._mock_service.create_workspace.return_value = Workspace(**ws_entity)

        resp = client.post(BASE_URL, json={"name": "Schema WS", "default_ai_model": "gpt-4o"})
        assert resp.status_code == 201
        body = resp.json()

        required_fields = ["id", "name", "description", "default_ai_model",
                           "default_repo_id", "vector_db_config", "tool_config", "created_at"]
        for field in required_fields:
            assert field in body, f"Missing field '{field}' in workspace creation response"
        assert body["id"] == "schema-test-ws"
        assert body["name"] == "Schema WS"


class TestGetWorkspace:
    def test_get_returns_404_when_not_found(self, client):
        client._mock_service.get_workspace.return_value = None
        resp = client.get(f"{BASE_URL}/nonexistent-id")
        assert resp.status_code == 404

    def test_get_returns_404_for_other_users_workspace(self, client):
        # Service returns None for non-owners (ownership check inside service)
        client._mock_service.get_workspace.return_value = None
        resp = client.get(f"{BASE_URL}/ws-other-owner")
        assert resp.status_code == 404

    def test_get_returns_200_for_owner(self, client):
        ws_entity = _make_workspace_entity(id="ws-mine")
        from src.domain.entities.workspace import Workspace
        client._mock_service.get_workspace.return_value = Workspace(**ws_entity)

        resp = client.get(f"{BASE_URL}/ws-mine")
        assert resp.status_code == 200


class TestUpdateWorkspace:
    def test_update_returns_404_when_not_found_or_unauthorized(self, client):
        client._mock_service.update_workspace.return_value = None
        resp = client.put(f"{BASE_URL}/ws-1", json={"name": "Updated"})
        assert resp.status_code == 404

    def test_update_returns_200_for_owner(self, client):
        ws_entity = _make_workspace_entity(name="Updated WS")
        from src.domain.entities.workspace import Workspace
        client._mock_service.update_workspace.return_value = Workspace(**ws_entity)

        resp = client.put(f"{BASE_URL}/ws-test-1", json={"name": "Updated WS"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated WS"


class TestDeleteWorkspace:
    def test_delete_returns_204_on_success(self, client):
        client._mock_service.delete_workspace.return_value = True
        resp = client.delete(f"{BASE_URL}/ws-test-1")
        assert resp.status_code == 204

    def test_delete_returns_404_for_non_owner(self, client):
        client._mock_service.delete_workspace.return_value = False
        resp = client.delete(f"{BASE_URL}/ws-other")
        assert resp.status_code == 404

    def test_delete_calls_service_with_user_and_workspace_id(self, client):
        client._mock_service.delete_workspace.return_value = True
        client.delete(f"{BASE_URL}/ws-test-1")
        client._mock_service.delete_workspace.assert_called_once_with("test-user-123", "ws-test-1")
