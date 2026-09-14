import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from src.application.services.project_service import ProjectService
from src.domain.entities.project import ProjectCreate, ProjectUpdate, ProjectStatus


def _make_db_project(id="proj-1", user_id="user-123", name="My Project", status="active",
                     repos=None, created_at=None, updated_at=None):
    db_p = MagicMock()
    db_p.id = id
    db_p.user_id = user_id
    db_p.workspace_id = None
    db_p.name = name
    db_p.description = "Project desc"
    db_p.status = status
    db_p.repositories = repos or []
    db_p.created_at = created_at if created_at is not None else datetime.now(timezone.utc)
    db_p.updated_at = updated_at if updated_at is not None else datetime.now(timezone.utc)
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

    # ── Regression tests: NULL updated_at / created_at (the production 500 cause) ──

    def test_to_entity_with_null_updated_at(self):
        """_to_entity must not raise when db row has updated_at=None (legacy data)."""
        db_p = _make_db_project(user_id=self.user_id, updated_at=None)
        entity = self.service._to_entity(db_p, self.user_id)
        assert entity.updated_at is not None
        assert entity.id == "proj-1"
        assert entity.status == ProjectStatus.ACTIVE

    def test_to_entity_with_null_created_at(self):
        """_to_entity must not raise when both created_at and updated_at are None."""
        db_p = _make_db_project(user_id=self.user_id, created_at=None, updated_at=None)
        entity = self.service._to_entity(db_p, self.user_id)
        assert entity.created_at is not None
        assert entity.updated_at is not None

    def test_to_entity_with_null_status(self):
        """_to_entity must default status to ACTIVE when status is None."""
        db_p = _make_db_project(user_id=self.user_id, status=None)
        entity = self.service._to_entity(db_p, self.user_id)
        assert entity.status == ProjectStatus.ACTIVE

    def test_to_entity_with_empty_string_status(self):
        """_to_entity must default status to ACTIVE when status is empty string."""
        db_p = _make_db_project(user_id=self.user_id, status="")
        entity = self.service._to_entity(db_p, self.user_id)
        assert entity.status == ProjectStatus.ACTIVE

    def test_to_entity_with_unknown_status(self):
        """_to_entity must gracefully handle unexpected status values."""
        db_p = _make_db_project(user_id=self.user_id, status="UNKNOWN_STATUS")
        entity = self.service._to_entity(db_p, self.user_id)
        assert entity.status == ProjectStatus.ACTIVE

    def test_to_entity_with_archived_status_casing(self):
        """_to_entity handles ARCHIVED/Archived/archived variations."""
        for s in ("ARCHIVED", "Archived", "archived"):
            db_p = _make_db_project(user_id=self.user_id, status=s)
            entity = self.service._to_entity(db_p, self.user_id)
            assert entity.status == ProjectStatus.ARCHIVED, f"Failed for status={s!r}"

    def test_list_projects_with_null_updated_at(self):
        """list_projects must succeed even when all projects have updated_at=None."""
        db_projects = [
            _make_db_project(id=f"proj-{i}", user_id=self.user_id, updated_at=None)
            for i in range(3)
        ]
        self.mock_p_repo.list_by_user.return_value = db_projects

        result = self.service.list_projects(self.user_id)
        assert len(result) == 3
        for p in result:
            assert p.updated_at is not None

