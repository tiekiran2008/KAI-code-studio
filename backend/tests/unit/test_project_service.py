import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from src.application.services.project_service import ProjectService
from src.domain.entities.project import ProjectCreate, ProjectUpdate, ProjectStatus


def _make_db_project(id="proj-1", user_id="user-123", name="My Project", status="active", repos=None):
    db_p = MagicMock()
    db_p.id = id
    db_p.user_id = user_id
    db_p.workspace_id = None
    db_p.name = name
    db_p.description = "Project desc"
    db_p.status = status
    db_p.repositories = repos or []
    db_p.created_at = datetime.now(timezone.utc)
    db_p.updated_at = datetime.now(timezone.utc)
    return db_p


class TestProjectService:
    def setup_method(self):
        self.mock_p_repo = MagicMock()
        self.mock_r_service = MagicMock()
        self.service = ProjectService(self.mock_p_repo, self.mock_r_service)
        self.user_id = "user-123"

    def test_create_project(self):
        self.mock_p_repo.create.return_value = _make_db_project()
        data = ProjectCreate(name="My Project")

        res = self.service.create_project(self.user_id, data)
        assert res.name == "My Project"
        assert res.status == ProjectStatus.ACTIVE

    def test_get_project_unauthorized(self):
        db_p = _make_db_project(user_id="other-user")
        self.mock_p_repo.get_by_id.return_value = db_p

        res = self.service.get_project(self.user_id, "proj-1")
        assert res is None

    def test_archive_project(self):
        db_p = _make_db_project(user_id=self.user_id)
        self.mock_p_repo.get_by_id.return_value = db_p
        self.mock_p_repo.update.return_value = _make_db_project(status="archived")

        res = self.service.archive_project(self.user_id, "proj-1")
        assert res is not None
        assert res.status == ProjectStatus.ARCHIVED

    def test_link_repository(self):
        db_p = _make_db_project(user_id=self.user_id)
        self.mock_p_repo.get_by_id.return_value = db_p
        self.mock_r_service.get_repository.return_value = MagicMock(id="repo-1")

        self.service.link_repository(self.user_id, "proj-1", "repo-1")
        self.mock_p_repo.link_repository.assert_called_once_with("proj-1", "repo-1")
