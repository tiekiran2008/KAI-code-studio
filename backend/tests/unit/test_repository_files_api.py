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


def test_repository_service_tree_fallback_to_vector_db(tmp_path):
    mock_db_repo = MagicMock()
    mock_db_repo.id = "repo-fallback"
    mock_db_repo.user_id = "user-1"
    mock_db_repo.url = "https://github.com/test/repo-fallback"

    mock_repo_repo = MagicMock()
    mock_repo_repo.get_by_id.return_value = mock_db_repo

    mock_vector_db = MagicMock()
    mock_vector_db.get_indexed_files.return_value = {
        "src/app.py",
        "src/utils/helper.py",
        "README.md",
    }

    from src.core.config import settings
    old_root = settings.WORKSPACE_ROOT
    # Point workspace root to an empty tmp_path so repo dir does not exist
    settings.WORKSPACE_ROOT = str(tmp_path / "empty_workspace")

    try:
        svc = RepositoryService(
            repo_repository=mock_repo_repo,
            vector_db=mock_vector_db,
        )

        tree = svc.get_file_tree("user-1", "repo-fallback")
        mock_vector_db.get_indexed_files.assert_called_once_with("codebase_chunks", "repo-fallback")

        assert len(tree) == 2
        # Directories sorted first or alphabetic
        # root has "src" (dir) and "README.md" (file)
        names = [n.name for n in tree]
        assert "src" in names
        assert "README.md" in names

        src_node = next(n for n in tree if n.name == "src")
        assert src_node.type == "directory"
        assert len(src_node.children) == 2
        src_child_names = [c.name for c in src_node.children]
        assert "app.py" in src_child_names
        assert "utils" in src_child_names

        utils_node = next(c for c in src_node.children if c.name == "utils")
        assert utils_node.type == "directory"
        assert len(utils_node.children) == 1
        assert utils_node.children[0].name == "helper.py"
        assert utils_node.children[0].path == "src/utils/helper.py"

    finally:
        settings.WORKSPACE_ROOT = old_root


def test_get_file_content_fallback_to_vector_db_when_disk_missing(tmp_path):
    """When the local disk directory is missing, reconstruct file from Qdrant chunks."""
    mock_db_repo = MagicMock()
    mock_db_repo.id = "repo-qdrant-content"
    mock_db_repo.user_id = "user-1"
    mock_db_repo.url = "https://github.com/test/repo-qdrant"

    mock_repo_repo = MagicMock()
    mock_repo_repo.get_by_id.return_value = mock_db_repo

    # Simulate multi-chunk file with overlapping line windows (e.g. lines 1-4, lines 3-6)
    mock_vector_db = MagicMock()
    mock_vector_db.get_file_chunks.return_value = [
        {
            "id": "chunk-1",
            "repo_id": "repo-qdrant-content",
            "file_path": "main.py",
            "content": "line1\nline2\nline3\nline4",
            "language": "python",
            "start_line": 1,
            "end_line": 4,
        },
        {
            "id": "chunk-2",
            "repo_id": "repo-qdrant-content",
            "file_path": "main.py",
            "content": "line3\nline4\nline5\nline6",
            "language": "python",
            "start_line": 3,
            "end_line": 6,
        },
    ]

    from src.core.config import settings
    old_root = settings.WORKSPACE_ROOT
    settings.WORKSPACE_ROOT = str(tmp_path / "ephemeral_empty")

    try:
        svc = RepositoryService(
            repo_repository=mock_repo_repo,
            vector_db=mock_vector_db,
        )

        res = svc.get_file_content("user-1", "repo-qdrant-content", "main.py")

        mock_vector_db.get_file_chunks.assert_called_once_with("codebase_chunks", "repo-qdrant-content", "main.py")
        assert res.path == "main.py"
        assert res.name == "main.py"
        assert res.language == "python"
        assert res.is_binary is False
        # Verify deduplication / exact line reconstruction: lines 1 to 6 without duplicates
        expected_content = "line1\nline2\nline3\nline4\nline5\nline6"
        assert res.content == expected_content

    finally:
        settings.WORKSPACE_ROOT = old_root


def test_get_file_content_nested_path_fallback(tmp_path):
    """Test fallback with nested directory path."""
    mock_db_repo = MagicMock()
    mock_db_repo.id = "repo-nested"
    mock_db_repo.user_id = "user-1"
    mock_db_repo.url = "https://github.com/test/repo-nested"

    mock_repo_repo = MagicMock()
    mock_repo_repo.get_by_id.return_value = mock_db_repo

    mock_vector_db = MagicMock()
    mock_vector_db.get_file_chunks.return_value = [
        {
            "id": "chunk-nested-1",
            "repo_id": "repo-nested",
            "file_path": "src/utils/math_helper.py",
            "content": "def add(a, b):\n    return a + b\n",
            "language": "python",
            "start_line": 1,
            "end_line": 2,
        }
    ]

    from src.core.config import settings
    old_root = settings.WORKSPACE_ROOT
    settings.WORKSPACE_ROOT = str(tmp_path / "ephemeral_empty")

    try:
        svc = RepositoryService(
            repo_repository=mock_repo_repo,
            vector_db=mock_vector_db,
        )

        res = svc.get_file_content("user-1", "repo-nested", "src/utils/math_helper.py")
        assert res.path == "src/utils/math_helper.py"
        assert res.name == "math_helper.py"
        assert "def add(a, b):" in res.content

    finally:
        settings.WORKSPACE_ROOT = old_root


def test_get_file_content_nonexistent_file_raises_404(tmp_path):
    """When file does not exist on disk AND not in Qdrant, raise FileNotFoundError."""
    mock_db_repo = MagicMock()
    mock_db_repo.id = "repo-empty"
    mock_db_repo.user_id = "user-1"
    mock_db_repo.url = "https://github.com/test/repo-empty"

    mock_repo_repo = MagicMock()
    mock_repo_repo.get_by_id.return_value = mock_db_repo

    mock_vector_db = MagicMock()
    mock_vector_db.get_file_chunks.return_value = []

    from src.core.config import settings
    old_root = settings.WORKSPACE_ROOT
    settings.WORKSPACE_ROOT = str(tmp_path / "ephemeral_empty")

    try:
        svc = RepositoryService(
            repo_repository=mock_repo_repo,
            vector_db=mock_vector_db,
        )

        with pytest.raises(FileNotFoundError):
            svc.get_file_content("user-1", "repo-empty", "nonexistent.py")

    finally:
        settings.WORKSPACE_ROOT = old_root


def test_get_file_content_path_traversal_and_sensitive_rejected(tmp_path):
    """Path traversal and sensitive file access must be rejected immediately."""
    mock_db_repo = MagicMock()
    mock_db_repo.id = "repo-secure"
    mock_db_repo.user_id = "user-1"
    mock_db_repo.url = "https://github.com/test/repo-secure"

    mock_repo_repo = MagicMock()
    mock_repo_repo.get_by_id.return_value = mock_db_repo

    mock_vector_db = MagicMock()

    from src.core.config import settings
    old_root = settings.WORKSPACE_ROOT
    settings.WORKSPACE_ROOT = str(tmp_path / "ephemeral_empty")

    try:
        svc = RepositoryService(
            repo_repository=mock_repo_repo,
            vector_db=mock_vector_db,
        )

        # 1. Traversal check
        with pytest.raises(ValueError):
            svc.get_file_content("user-1", "repo-secure", "../../etc/passwd")

        with pytest.raises(ValueError):
            svc.get_file_content("user-1", "repo-secure", "..\\..\\secret.txt")

        # 2. Sensitive file check
        with pytest.raises(PermissionError):
            svc.get_file_content("user-1", "repo-secure", ".env")

    finally:
        settings.WORKSPACE_ROOT = old_root


def test_qdrant_adapter_get_file_chunks_real_schema_and_filter():
    """Verify QdrantAdapter.get_file_chunks uses repo_id scroll filter and in-memory matching on real schema."""
    from src.infrastructure.vector_db.qdrant_adapter import QdrantAdapter

    mock_client = MagicMock()
    adapter = QdrantAdapter(url="http://mock-qdrant:6333")
    adapter.client = mock_client

    # Create mock scored points with real stored Qdrant payload schema
    point_readme = MagicMock()
    point_readme.id = "chunk-uuid-1"
    point_readme.payload = {
        "repo_id": "dd2026d2-6746-4b3e-ad7c-48156609f455",
        "file_path": "README.md",
        "content": "# AI Skill Analyzer\nAnalyzes skills efficiently.",
        "language": "markdown",
        "commit_hash": "HEAD",
        "symbol_name": "file_root",
        "symbol_type": "module",
        "start_line": 1,
        "end_line": 2,
    }

    point_gitignore = MagicMock()
    point_gitignore.id = "chunk-uuid-2"
    point_gitignore.payload = {
        "repo_id": "dd2026d2-6746-4b3e-ad7c-48156609f455",
        "file_path": ".gitignore",
        "content": "node_modules/\n__pycache__/\n",
        "language": "ignore",
        "commit_hash": "HEAD",
        "symbol_name": None,
        "symbol_type": None,
        "start_line": 1,
        "end_line": 2,
    }

    mock_client.scroll.return_value = ([point_readme, point_gitignore], None)

    # 1. Retrieve README.md
    chunks = adapter.get_file_chunks("codebase_chunks", "dd2026d2-6746-4b3e-ad7c-48156609f455", "README.md")
    assert len(chunks) == 1
    assert chunks[0]["file_path"] == "README.md"
    assert chunks[0]["content"] == "# AI Skill Analyzer\nAnalyzes skills efficiently."
    assert chunks[0]["start_line"] == 1
    assert chunks[0]["end_line"] == 2

    # Verify filter uses ONLY repo_id (no unindexed field errors)
    scroll_args = mock_client.scroll.call_args[1]
    scroll_filter = scroll_args["scroll_filter"]
    assert len(scroll_filter.must) == 1
    assert scroll_filter.must[0].key == "repo_id"
    assert scroll_filter.must[0].match.value == "dd2026d2-6746-4b3e-ad7c-48156609f455"

    # 2. Retrieve .gitignore
    chunks_git = adapter.get_file_chunks("codebase_chunks", "dd2026d2-6746-4b3e-ad7c-48156609f455", ".gitignore")
    assert len(chunks_git) == 1
    assert chunks_git[0]["file_path"] == ".gitignore"
    assert "node_modules/" in chunks_git[0]["content"]


def test_qdrant_adapter_get_file_chunks_error_propagates():
    """Verify that a Qdrant communication/scroll error is raised as RuntimeError and not masked as 404."""
    from src.infrastructure.vector_db.qdrant_adapter import QdrantAdapter

    mock_client = MagicMock()
    mock_client.scroll.side_effect = Exception("400 Bad Request: Collection not found")

    adapter = QdrantAdapter(url="http://mock-qdrant:6333")
    adapter.client = mock_client

    with pytest.raises(RuntimeError) as excinfo:
        adapter.get_file_chunks("codebase_chunks", "repo-123", "main.py")
    assert "Vector database error during chunk retrieval" in str(excinfo.value)



