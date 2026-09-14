import pytest
from unittest.mock import MagicMock
from pathlib import Path
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import (
    get_current_user,
    get_repository_service,
)
from src.domain.entities.repository import (
    Repository,
    RepositoryProvider,
    IndexingStatus,
    FileNode,
    FileContentResponse,
)
from src.application.services.repository_service import RepositoryService


@pytest.fixture
def mock_user():
    return {"sub": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def mock_repo_service():
    service = MagicMock()
    fake_tree = [
        FileNode(
            id="dir-repo-123-src",
            name="src",
            path="src",
            type="directory",
            children=[
                FileNode(
                    id="file-repo-123-src/main.py",
                    name="main.py",
                    path="src/main.py",
                    type="file",
                    size=120,
                    language="python",
                )
            ],
        ),
        FileNode(
            id="file-repo-123-README.md",
            name="README.md",
            path="README.md",
            type="file",
            size=45,
            language="markdown",
        ),
    ]
    service.get_file_tree.return_value = fake_tree
    service.get_file_content.return_value = FileContentResponse(
        path="README.md",
        name="README.md",
        content="# Test Project",
        size=14,
        language="markdown",
        is_binary=False,
    )
    return service


def test_get_repository_tree_api(mock_user, mock_repo_service):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service

    client = TestClient(app)
    response = client.get("/api/v1/repositories/repo-123/tree")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "src"
    assert data[0]["type"] == "directory"
    assert len(data[0]["children"]) == 1
    assert data[0]["children"][0]["name"] == "main.py"
    assert data[1]["name"] == "README.md"
    assert data[1]["type"] == "file"

    app.dependency_overrides.clear()


def test_get_repository_file_content_api(mock_user, mock_repo_service):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_repository_service] = lambda: mock_repo_service

    client = TestClient(app)
    response = client.get("/api/v1/repositories/repo-123/files/content?path=README.md")

    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "README.md"
    assert data["name"] == "README.md"
    assert data["content"] == "# Test Project"
    assert data["language"] == "markdown"
    assert data["is_binary"] is False

    app.dependency_overrides.clear()


def test_repository_service_real_tree_and_traversal_protection(tmp_path):
    # Create a temporary repository directory structure
    repo_dir = tmp_path / "repos" / "repo-abc"
    repo_dir.mkdir(parents=True)
    (repo_dir / "README").write_text("Hello World!\n", encoding="utf-8")
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("print('hello')", encoding="utf-8")
    (repo_dir / ".env").write_text("SECRET=123", encoding="utf-8")

    mock_db_repo = MagicMock()
    mock_db_repo.id = "repo-abc"
    mock_db_repo.user_id = "user-1"
    mock_db_repo.url = ""

    mock_repo_repo = MagicMock()
    mock_repo_repo.get_by_id.return_value = mock_db_repo

    from src.core.config import settings
    old_root = settings.WORKSPACE_ROOT
    settings.WORKSPACE_ROOT = str(tmp_path)

    try:
        svc = RepositoryService(repo_repository=mock_repo_repo)
        
        # Test tree listing
        tree = svc.get_file_tree("user-1", "repo-abc")
        paths = [n.path for n in tree]
        assert "README" in paths
        assert "src" in paths
        # .env should be excluded from tree
        assert ".env" not in paths

        # Test valid content read
        readme_content = svc.get_file_content("user-1", "repo-abc", "README")
        assert readme_content.content == "Hello World!\n"
        assert readme_content.name == "README"

        # Test sensitive file read rejection
        with pytest.raises(PermissionError):
            svc.get_file_content("user-1", "repo-abc", ".env")

        # Test directory traversal attack rejection
        with pytest.raises(Exception):
            svc.get_file_content("user-1", "repo-abc", "../../secret.txt")

        # Test non-existent file
        with pytest.raises(FileNotFoundError):
            svc.get_file_content("user-1", "repo-abc", "does_not_exist.txt")

    finally:
        settings.WORKSPACE_ROOT = old_root
