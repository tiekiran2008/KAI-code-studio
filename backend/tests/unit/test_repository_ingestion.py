import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.services.index_manager import IndexManager
from src.application.services.repository_ingestion_service import (
    RepositoryIngestionService,
    RepositoryIndexProgress,
)
from src.domain.interfaces.embedding import IEmbeddingService
from src.domain.interfaces.vector_db import IVectorDB
from src.domain.models.chunk import SemanticChunk
from src.infrastructure.repositories.repository_repository import RepositoryRepository


class MockEmbeddingService(IEmbeddingService):
    def generate_embedding(self, text: str):
        return [0.1] * 384

    def generate_embeddings(self, texts):
        return [[0.1] * 384 for _ in texts]

    @property
    def dimension(self) -> int:
        return 384


class MockVectorDB(IVectorDB):
    def __init__(self):
        self.stored_chunks = {}
        self.collections = set()

    def ensure_collection(self, collection_name: str, vector_size: int):
        self.collections.add(collection_name)

    def upsert_chunks(self, collection_name: str, chunks, embeddings):
        if collection_name not in self.stored_chunks:
            self.stored_chunks[collection_name] = []
        for c in chunks:
            self.stored_chunks[collection_name].append(c)

    def delete_by_file(self, collection_name: str, repo_id: str, file_path: str):
        if collection_name in self.stored_chunks:
            self.stored_chunks[collection_name] = [
                c for c in self.stored_chunks[collection_name]
                if not (c.repo_id == repo_id and c.file_path == file_path)
            ]

    def delete_by_repo(self, collection_name: str, repo_id: str):
        if collection_name in self.stored_chunks:
            self.stored_chunks[collection_name] = [
                c for c in self.stored_chunks[collection_name]
                if c.repo_id != repo_id
            ]

    def search(self, collection_name: str, query_embedding, filter_metadata=None, limit=10):
        chunks = self.stored_chunks.get(collection_name, [])
        if filter_metadata and "repo_id" in filter_metadata:
            target_repo = filter_metadata["repo_id"]
            chunks = [c for c in chunks if c.repo_id == target_repo]

        results = []
        for c in chunks[:limit]:
            results.append({
                "id": c.id,
                "score": 0.95,
                "repo_id": c.repo_id,
                "file_path": c.file_path,
                "content": c.content,
                "language": c.language,
                "symbol_name": c.symbol_name,
                "symbol_type": c.symbol_type,
                "start_line": c.start_line,
                "end_line": c.end_line,
            })
        return results

    def get_indexed_files(self, collection_name: str, repo_id: str):
        chunks = self.stored_chunks.get(collection_name, [])
        return {c.file_path for c in chunks if c.repo_id == repo_id}



def test_repository_ingestion_end_to_end():
    # 1. Create a temporary local repository folder
    temp_dir = tempfile.mkdtemp()
    try:
        src_dir = os.path.join(temp_dir, "src")
        os.makedirs(src_dir, exist_ok=True)

        with open(os.path.join(src_dir, "auth.py"), "w") as f:
            f.write("class AuthService:\n    def login(self, u, p):\n        return True\n")

        with open(os.path.join(src_dir, "utils.ts"), "w") as f:
            f.write("export function formatName(name: string) { return name.trim(); }\n")

        # Add a secret file that must be skipped by FileFilter
        with open(os.path.join(temp_dir, ".env"), "w") as f:
            f.write("SECRET_KEY=super_secret_12345\n")

        # 2. Setup mocks
        emb_service = MockEmbeddingService()
        vector_db = MockVectorDB()
        index_manager = IndexManager(emb_service, vector_db)

        mock_db_repo = MagicMock()
        mock_db_repo.id = "repo-xyz-789"
        mock_db_repo.url = temp_dir
        mock_db_repo.provider = "local"
        mock_db_repo.default_branch = "main"
        mock_db_repo.git_access_token_encrypted = None

        repo_repository = MagicMock()
        repo_repository.get_by_id.return_value = mock_db_repo

        # 3. Ingest repository
        service = RepositoryIngestionService(index_manager, repo_repository)
        indexed_count = service.ingest_repository("repo-xyz-789", "user-1")

        assert indexed_count > 0
        repo_repository.set_indexing_status.assert_called_with(
            repo_id="repo-xyz-789", status="indexed", chunks_count=indexed_count
        )

        # 4. Verify vector database content & security filtering
        stored = vector_db.stored_chunks.get("codebase_chunks", [])
        assert len(stored) == indexed_count

        # Ensure .env was NOT indexed
        file_paths = [c.file_path for c in stored]
        assert not any(".env" in p for p in file_paths)
        assert any("auth.py" in p for p in file_paths)
        assert any("utils.ts" in p for p in file_paths)

        # 5. Verify progress tracking
        progress = service.get_progress("repo-xyz-789")
        assert progress.status in ("indexed", "completed")
        assert progress.progress == 100.0
        assert progress.files_processed >= 2

        # 6. Verify Re-indexing cleans previous vectors
        reindexed_count = service.ingest_repository("repo-xyz-789", "user-1")
        assert reindexed_count == indexed_count
        assert len(vector_db.stored_chunks["codebase_chunks"]) == indexed_count

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_repository_ingestion_failure_handling():
    emb_service = MockEmbeddingService()
    vector_db = MockVectorDB()
    index_manager = IndexManager(emb_service, vector_db)

    mock_db_repo = MagicMock()
    mock_db_repo.id = "repo-fail-001"
    mock_db_repo.url = "local:///non/existent/path/that/does/not/exist"
    mock_db_repo.provider = "local"
    mock_db_repo.default_branch = "main"
    mock_db_repo.git_access_token_encrypted = None

    repo_repository = MagicMock()
    repo_repository.get_by_id.return_value = mock_db_repo

    service = RepositoryIngestionService(index_manager, repo_repository)
    indexed_count = service.ingest_repository("repo-fail-001", "user-1")

    assert indexed_count == 0
    progress = service.get_progress("repo-fail-001")
    assert progress.status == "failed"
    assert progress.error is not None
