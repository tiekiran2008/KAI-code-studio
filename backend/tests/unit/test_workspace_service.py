"""
Unit Tests: WorkspaceService
============================
Tests for the WorkspaceService business logic layer, including
ownership validation and CRUD operations using a mocked repository.
"""
import pytest
import uuid
from unittest.mock import MagicMock, PropertyMock, patch
from datetime import datetime

from src.application.services.workspace_service import WorkspaceService
from src.domain.entities.workspace import WorkspaceCreate, WorkspaceUpdate


def _make_db_workspace(
    id="ws-1",
    user_id="user-abc",
    name="Test WS",
    description="A test workspace",
    default_ai_model="gpt-4o",
    default_repo_id=None,
    vector_db_config=None,
    tool_config=None,
    repositories=None,
):
    """Helper to build a mock DBWorkspace object."""
    db_ws = MagicMock()
    db_ws.id = id
    db_ws.user_id = user_id
    db_ws.name = name
    db_ws.description = description
    db_ws.default_ai_model = default_ai_model
    db_ws.default_repo_id = default_repo_id
    db_ws.vector_db_config = vector_db_config or {}
    db_ws.tool_config = tool_config or {}
    db_ws.repositories = repositories or []
    db_ws.created_at = datetime(2024, 1, 1, 12, 0, 0)
    db_ws.updated_at = datetime(2024, 6, 1, 12, 0, 0)
    return db_ws


class TestWorkspaceService:
    def setup_method(self):
        self.mock_repo = MagicMock()
        self.service = WorkspaceService(self.mock_repo)
        self.user_id = "user-abc"
        self.other_user_id = "user-xyz"
        self.workspace_id = "ws-1"

    # ---------------------------------------------------------------
    # create_workspace
    # ---------------------------------------------------------------
    def test_create_workspace_returns_entity(self):
        db_ws = _make_db_workspace(id=self.workspace_id, user_id=self.user_id)
        self.mock_repo.create.return_value = db_ws

        data = WorkspaceCreate(name="Test WS", default_ai_model="gpt-4o")
        result = self.service.create_workspace(self.user_id, data)

        self.mock_repo.create.assert_called_once()
        assert result.id == self.workspace_id
        assert result.user_id == self.user_id
        assert result.name == "Test WS"

    def test_create_workspace_passes_user_id_to_repo(self):
        db_ws = _make_db_workspace(user_id=self.user_id)
        self.mock_repo.create.return_value = db_ws

        data = WorkspaceCreate(name="New WS", default_ai_model="gpt-4o")
        self.service.create_workspace(self.user_id, data)

        call_args = self.mock_repo.create.call_args
        assert call_args[0][0] == self.user_id

    def test_create_workspace_id_is_valid_uuid(self):
        """The workspace repository must generate a valid UUID v4 as the primary key."""
        from src.infrastructure.repositories.workspace_repository import WorkspaceRepository
        from src.infrastructure.persistence.workspace_models import DBWorkspace
        from sqlalchemy.orm import Session

        mock_session = MagicMock(spec=Session)
        # Capture the object being added
        added_objects = []
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)
        mock_session.refresh.side_effect = lambda obj: None

        repo = WorkspaceRepository(mock_session)
        data = {"name": "UUID Test WS", "default_ai_model": "gpt-4o"}
        try:
            repo.create("user-1", data)
        except Exception:
            pass  # commit may fail without a real DB; we only care about the ID

        assert added_objects, "No object was added to the session"
        created = added_objects[0]
        assert hasattr(created, "id")
        parsed = uuid.UUID(created.id)  # Raises ValueError if not a valid UUID
        assert str(parsed) == created.id

    def test_create_workspace_empty_default_repo_id_coerced_to_none(self):
        """Service must convert empty-string default_repo_id to None to avoid FK violation."""
        captured_data = {}

        def fake_create(user_id, data):
            captured_data.update(data)
            return _make_db_workspace(user_id=user_id, default_repo_id=None)

        self.mock_repo.create.side_effect = fake_create

        data = WorkspaceCreate(name="Empty Repo WS", default_ai_model="gpt-4o", default_repo_id="")
        self.service.create_workspace(self.user_id, data)

        assert captured_data.get("default_repo_id") is None, (
            "Empty-string default_repo_id should be coerced to None before reaching the repository"
        )

    def test_create_workspace_updated_at_is_none_after_insert(self):
        """updated_at is NULL right after INSERT (onupdate fires on UPDATE only)."""
        db_ws = _make_db_workspace(user_id=self.user_id)
        db_ws.updated_at = None  # Simulate the DB returning NULL after INSERT
        self.mock_repo.create.return_value = db_ws

        data = WorkspaceCreate(name="Insert WS", default_ai_model="gpt-4o")
        result = self.service.create_workspace(self.user_id, data)

        # updated_at must be accepted as None — it should not raise a validation error
        assert result.updated_at is None

    # ---------------------------------------------------------------
    # get_workspace
    # ---------------------------------------------------------------
    def test_get_workspace_returns_entity_for_owner(self):
        db_ws = _make_db_workspace(id=self.workspace_id, user_id=self.user_id)
        self.mock_repo.get_by_id.return_value = db_ws

        result = self.service.get_workspace(self.user_id, self.workspace_id)

        assert result is not None
        assert result.id == self.workspace_id

    def test_get_workspace_returns_none_for_non_owner(self):
        db_ws = _make_db_workspace(id=self.workspace_id, user_id=self.user_id)
        self.mock_repo.get_by_id.return_value = db_ws

        # Different user tries to access
        result = self.service.get_workspace(self.other_user_id, self.workspace_id)

        assert result is None

    def test_get_workspace_returns_none_when_not_found(self):
        self.mock_repo.get_by_id.return_value = None

        result = self.service.get_workspace(self.user_id, "nonexistent-id")

        assert result is None

    # ---------------------------------------------------------------
    # list_workspaces
    # ---------------------------------------------------------------
    def test_list_workspaces_returns_only_user_workspaces(self):
        db_ws1 = _make_db_workspace(id="ws-1", user_id=self.user_id, name="Alpha")
        db_ws2 = _make_db_workspace(id="ws-2", user_id=self.user_id, name="Beta")
        self.mock_repo.get_all_by_user.return_value = [db_ws1, db_ws2]

        result = self.service.list_workspaces(self.user_id)

        self.mock_repo.get_all_by_user.assert_called_once_with(self.user_id, 0, 100)
        assert len(result) == 2
        assert result[0].name == "Alpha"

    def test_list_workspaces_returns_empty_list(self):
        self.mock_repo.get_all_by_user.return_value = []

        result = self.service.list_workspaces(self.user_id)

        assert result == []

    # ---------------------------------------------------------------
    # update_workspace
    # ---------------------------------------------------------------
    def test_update_workspace_succeeds_for_owner(self):
        db_ws_original = _make_db_workspace(id=self.workspace_id, user_id=self.user_id, name="Old Name")
        db_ws_updated = _make_db_workspace(id=self.workspace_id, user_id=self.user_id, name="New Name")
        self.mock_repo.get_by_id.return_value = db_ws_original
        self.mock_repo.update.return_value = db_ws_updated

        data = WorkspaceUpdate(name="New Name")
        result = self.service.update_workspace(self.user_id, self.workspace_id, data)

        assert result is not None
        assert result.name == "New Name"

    def test_update_workspace_returns_none_for_non_owner(self):
        db_ws = _make_db_workspace(id=self.workspace_id, user_id=self.user_id)
        self.mock_repo.get_by_id.return_value = db_ws

        data = WorkspaceUpdate(name="Stolen Name")
        result = self.service.update_workspace(self.other_user_id, self.workspace_id, data)

        assert result is None
        self.mock_repo.update.assert_not_called()

    def test_update_workspace_returns_none_when_not_found(self):
        self.mock_repo.get_by_id.return_value = None

        data = WorkspaceUpdate(name="New Name")
        result = self.service.update_workspace(self.user_id, "nonexistent-id", data)

        assert result is None

    # ---------------------------------------------------------------
    # delete_workspace
    # ---------------------------------------------------------------
    def test_delete_workspace_succeeds_for_owner(self):
        db_ws = _make_db_workspace(id=self.workspace_id, user_id=self.user_id)
        self.mock_repo.get_by_id.return_value = db_ws
        self.mock_repo.delete.return_value = True

        result = self.service.delete_workspace(self.user_id, self.workspace_id)

        assert result is True
        self.mock_repo.delete.assert_called_once_with(self.workspace_id)

    def test_delete_workspace_returns_false_for_non_owner(self):
        db_ws = _make_db_workspace(id=self.workspace_id, user_id=self.user_id)
        self.mock_repo.get_by_id.return_value = db_ws

        result = self.service.delete_workspace(self.other_user_id, self.workspace_id)

        assert result is False
        self.mock_repo.delete.assert_not_called()

    def test_delete_workspace_returns_false_when_not_found(self):
        self.mock_repo.get_by_id.return_value = None

        result = self.service.delete_workspace(self.user_id, "nonexistent-id")

        assert result is False

    # ---------------------------------------------------------------
    # repo_count
    # ---------------------------------------------------------------
    def test_repo_count_is_computed_correctly(self):
        mock_repos = [MagicMock(), MagicMock(), MagicMock()]
        db_ws = _make_db_workspace(user_id=self.user_id, repositories=mock_repos)
        self.mock_repo.create.return_value = db_ws

        data = WorkspaceCreate(name="WS With Repos", default_ai_model="gpt-4o")
        result = self.service.create_workspace(self.user_id, data)

        assert result.repo_count == 3
