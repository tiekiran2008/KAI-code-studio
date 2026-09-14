import pytest
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.interfaces.api.dependencies import get_current_user, get_repository_service
from src.core.config import settings
from src.domain.entities.repository import (
    Repository,
    RepositoryProvider,
    IndexingStatus,
)
from src.application.services.repository_service import RepositoryService


def test_real_hello_world_repository_tree_and_content():
    """Verify live behavior with octocat/Hello-World repo (8c3ab38b-df87-461f-a036-38c749e07f99)."""
    repo_id = "8c3ab38b-df87-461f-a036-38c749e07f99"
    repo_path = Path(settings.WORKSPACE_ROOT).resolve() / "repos" / repo_id

    # Check if the repo exists in workspace
    if not repo_path.exists():
        pytest.skip(f"Repository {repo_id} not cloned in {repo_path}")

    # Set up mock DB repository returning the Hello-World repo metadata
    mock_db_repo = MagicMock()
    mock_db_repo.id = repo_id
    mock_db_repo.user_id = "test-user-admin"
    mock_db_repo.url = "https://github.com/octocat/Hello-World"
    mock_db_repo.name = "Hello-World"
    mock_db_repo.default_branch = "master"
    mock_db_repo.current_branch = "master"
    mock_db_repo.branches_json = ["master"]
    mock_db_repo.indexing_status = "indexed"
    mock_db_repo.chunks_count = 1
    mock_db_repo.language_stats_json = []
    mock_db_repo.detected_stack_json = {}

    mock_repo_repo = MagicMock()
    mock_repo_repo.get_by_id.return_value = mock_db_repo

    real_service = RepositoryService(repo_repository=mock_repo_repo)

    # Set dependency overrides
    app.dependency_overrides[get_current_user] = lambda: {"sub": "test-user-admin", "email": "admin@example.com"}
    app.dependency_overrides[get_repository_service] = lambda: real_service

    try:
        client = TestClient(app)

        # 1. Fetch Real File Tree
        res_tree = client.get(f"/api/v1/repositories/{repo_id}/tree")
        assert res_tree.status_code == 200, f"Tree API failed: {res_tree.text}"
        tree = res_tree.json()
        assert isinstance(tree, list)
        file_names = [f["name"] for f in tree]
        assert "README" in file_names or "README.md" in file_names
        assert ".git" not in file_names  # .git must be excluded!

        # 2. Fetch Real File Content for README
        readme_name = "README" if "README" in file_names else "README.md"
        res_content = client.get(f"/api/v1/repositories/{repo_id}/files/content?path={readme_name}")
        assert res_content.status_code == 200, f"Content API failed: {res_content.text}"
        content_data = res_content.json()
        assert content_data["name"] == readme_name
        assert "Hello World" in content_data["content"]
        assert content_data["is_binary"] is False

        # 3. Security: Path Traversal Attacks against real repo directory
        res_trav = client.get(f"/api/v1/repositories/{repo_id}/files/content?path=../../.env")
        assert res_trav.status_code in (400, 403, 404)

        res_trav_win = client.get(f"/api/v1/repositories/{repo_id}/files/content?path=..\\..\\.env")
        assert res_trav_win.status_code in (400, 403, 404)

        res_abs = client.get(f"/api/v1/repositories/{repo_id}/files/content?path=/etc/passwd")
        assert res_abs.status_code in (400, 404)

        res_nonexist = client.get(f"/api/v1/repositories/{repo_id}/files/content?path=not_found_file.txt")
        assert res_nonexist.status_code == 404

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rag_retrieval_filtering_by_repo_id():
    """Verify that RAG search strictly filters chunks by the target repository ID."""
    from src.application.rag.hybrid_retriever import SemanticRetriever

    mock_emb_svc = MagicMock()
    mock_emb_svc.generate_embedding.return_value = [0.1] * 384
    mock_emb_svc.dimension = 384

    mock_vector_db = MagicMock()
    # Return chunks only for repo-target
    target_repo_id = "8c3ab38b-df87-461f-a036-38c749e07f99"
    other_repo_id = "other-repo-999"

    def mock_search(collection_name, query_vector, filter_dict, limit):
        if filter_dict.get("repo_id") == target_repo_id:
            return [{
                "id": "chunk-hello-1",
                "repo_id": target_repo_id,
                "file_path": "README",
                "content": "Hello World!",
                "language": "markdown",
                "score": 0.95,
            }]
        return []

    mock_vector_db.search.side_effect = mock_search

    retriever = SemanticRetriever(mock_emb_svc, mock_vector_db)
    results = await retriever.retrieve("Hello", target_repo_id, limit=5)

    assert len(results) == 1
    assert results[0].chunk.repo_id == target_repo_id
    assert results[0].chunk.file_path == "README"
    assert "Hello World" in results[0].chunk.content

    # Querying a different repo should not return Hello-World chunks
    other_results = await retriever.retrieve("Hello", other_repo_id, limit=5)
    assert len(other_results) == 0


