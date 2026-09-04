import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from src.application.services.repository_service import RepositoryService
from src.domain.entities.repository import RepositoryCreate, RepositoryUpdate, IndexingStatus


def _make_db_repo(
    id="repo-1",
    user_id="user-123",
    url="https://github.com/owner/my-repo",
    name="my-repo",
    provider="github",
    default_branch="main",
    current_branch="main",
    indexing_status="indexed",
    chunks_count=128,
):
    db_r = MagicMock()
    db_r.id = id
    db_r.user_id = user_id
    db_r.workspace_id = None
    db_r.url = url
    db_r.name = name
    db_r.provider = provider
    db_r.description = "Test repo"
    db_r.owner = "owner"
    db_r.default_branch = default_branch
    db_r.current_branch = current_branch
    db_r.branches_json = [default_branch, "main", "dev"]
    db_r.repo_size_kb = 1024
    db_r.language_stats_json = [{"language": "Python", "percentage": 100.0, "bytes": 10000}]
    db_r.detected_stack_json = {"language": "Python", "framework": "FastAPI"}
    db_r.indexing_status = indexing_status
    db_r.chunks_count = chunks_count
    db_r.last_indexed_at = datetime.now(timezone.utc)
    db_r.is_private = False
    db_r.stars = 42
    db_r.created_at = datetime.now(timezone.utc)
    db_r.updated_at = datetime.now(timezone.utc)
    return db_r


class TestRepositoryService:
    def setup_method(self):
        self.mock_repo = MagicMock()
        self.mock_detector = MagicMock()
        self.service = RepositoryService(self.mock_repo, self.mock_detector)
        self.user_id = "user-123"

    def test_import_repository_prevents_duplicate(self):
        self.mock_repo.get_by_user_and_url.return_value = _make_db_repo()
        data = RepositoryCreate(url="https://github.com/owner/my-repo")

        with pytest.raises(ValueError, match="already been imported"):
            self.service.import_repository(self.user_id, data)

    def test_import_repository_success(self):
        self.mock_repo.get_by_user_and_url.return_value = None
        self.mock_detector.detect_provider.return_value = MagicMock(value="github")
        self.mock_detector.extract_owner_and_name.return_value = ("owner", "my-repo")
        self.mock_detector.detect.return_value = MagicMock(
            language="Python", framework="FastAPI", package_manager="pip", build_tool=None, test_framework="pytest",
            model_dump=lambda: {"language": "Python", "framework": "FastAPI"}
        )
        self.mock_repo.create.return_value = _make_db_repo()

        data = RepositoryCreate(url="https://github.com/owner/my-repo")
        res = self.service.import_repository(self.user_id, data)

        assert res.name == "my-repo"
        assert self.mock_repo.create.called

    def test_get_repository_ownership_check(self):
        db_r = _make_db_repo(user_id="other-user")
        self.mock_repo.get_by_id.return_value = db_r

        res = self.service.get_repository(self.user_id, "repo-1")
        assert res is None

    def test_switch_branch_success(self):
        db_r = _make_db_repo(user_id=self.user_id)
        self.mock_repo.get_by_id.return_value = db_r
        self.mock_repo.switch_branch.return_value = _make_db_repo(current_branch="feature-x")

        res = self.service.switch_branch(self.user_id, "repo-1", "feature-x")
        assert res is not None
        assert res.current_branch == "feature-x"

    def test_health_check_returns_healthy(self):
        db_r = _make_db_repo(user_id=self.user_id)
        self.mock_repo.get_by_id.return_value = db_r

        res = self.service.health_check(self.user_id, "repo-1")
        assert res.is_reachable is True
        assert res.latency_ms is not None
