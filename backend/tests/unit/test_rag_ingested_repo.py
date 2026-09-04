import asyncio
import os
import shutil
import tempfile
import pytest

from src.application.rag.hybrid_retriever import HybridRetriever
from src.application.rag.citation_generator import CitationGenerator
from src.application.services.index_manager import IndexManager
from src.application.services.repository_ingestion_service import RepositoryIngestionService
from src.domain.models.rag import ParsedQuery, RerankedChunk
from src.infrastructure.repositories.repository_repository import RepositoryRepository
from unittest.mock import MagicMock


class SimpleEmbeddingService:
    def generate_embedding(self, text: str):
        # deterministic pseudo embedding based on char ords
        val = (sum(ord(c) for c in text[:10]) % 100) / 100.0
        return [val] * 384

    def generate_embeddings(self, texts):
        return [self.generate_embedding(t) for t in texts]

    @property
    def dimension(self) -> int:
        return 384


class InMemoryVectorDB:
    def __init__(self):
        self.points = {}

    def ensure_collection(self, collection_name: str, vector_size: int):
        if collection_name not in self.points:
            self.points[collection_name] = []

    def upsert_chunks(self, collection_name: str, chunks, embeddings):
        if collection_name not in self.points:
            self.points[collection_name] = []
        for c, emb in zip(chunks, embeddings):
            self.points[collection_name].append({
                "id": c.id,
                "vector": emb,
                "payload": {
                    "repo_id": c.repo_id,
                    "file_path": c.file_path,
                    "content": c.content,
                    "language": c.language,
                    "commit_hash": c.commit_hash,
                    "symbol_name": c.symbol_name,
                    "symbol_type": c.symbol_type,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                }
            })

    def delete_by_file(self, collection_name: str, repo_id: str, file_path: str):
        if collection_name in self.points:
            self.points[collection_name] = [
                p for p in self.points[collection_name]
                if not (p["payload"].get("repo_id") == repo_id and p["payload"].get("file_path") == file_path)
            ]

    def delete_by_repo(self, collection_name: str, repo_id: str):
        if collection_name in self.points:
            self.points[collection_name] = [
                p for p in self.points[collection_name]
                if p["payload"].get("repo_id") != repo_id
            ]

    def search(self, collection_name: str, query_embedding, filter_metadata=None, limit=10):
        pts = self.points.get(collection_name, [])
        if filter_metadata and "repo_id" in filter_metadata:
            target = filter_metadata["repo_id"]
            pts = [p for p in pts if p["payload"].get("repo_id") == target]

        results = []
        for p in pts[:limit]:
            res = p["payload"].copy()
            res["score"] = 0.92
            res["id"] = p["id"]
            results.append(res)
        return results


@pytest.mark.asyncio
async def test_rag_retrieval_and_citations_on_ingested_repository():
    temp_dir = tempfile.mkdtemp()
    try:
        # 1. Create a mock repository with auth module
        auth_file = os.path.join(temp_dir, "auth_service.py")
        with open(auth_file, "w") as f:
            f.write(
                "class TokenValidator:\n"
                "    def validate_token(self, token: str) -> bool:\n"
                "        return len(token) > 10\n"
            )

        emb_service = SimpleEmbeddingService()
        vector_db = InMemoryVectorDB()
        index_manager = IndexManager(emb_service, vector_db)

        mock_db_repo = MagicMock()
        mock_db_repo.id = "repo-alpha-111"
        mock_db_repo.url = temp_dir
        mock_db_repo.provider = "local"
        mock_db_repo.default_branch = "main"
        mock_db_repo.git_access_token_encrypted = None

        repo_repository = MagicMock()
        repo_repository.get_by_id.return_value = mock_db_repo

        # 2. Ingest repo
        ingestion_svc = RepositoryIngestionService(index_manager, repo_repository)
        count = ingestion_svc.ingest_repository("repo-alpha-111", "user-1")
        assert count > 0

        # Also ingest a different repo to verify cross-repository isolation
        mock_db_repo_beta = MagicMock()
        mock_db_repo_beta.id = "repo-beta-222"
        mock_db_repo_beta.url = temp_dir
        mock_db_repo_beta.provider = "local"
        mock_db_repo_beta.default_branch = "main"
        mock_db_repo_beta.git_access_token_encrypted = None
        repo_repository.get_by_id.return_value = mock_db_repo_beta

        ingestion_svc.ingest_repository("repo-beta-222", "user-2")

        # 3. Query through HybridRetriever scoped to repo-alpha-111
        retriever = HybridRetriever(emb_service, vector_db)
        pq = ParsedQuery(
            original_query="how does TokenValidator validate tokens?",
            rewritten_queries=["TokenValidator validate_token"],
            detected_symbols=["validate_token", "TokenValidator"],
            detected_files=["auth_service.py"],
            repo_id="repo-alpha-111",
            intent="query",
        )

        results = await retriever.retrieve(pq, limit=5)
        assert len(results) > 0

        # Ensure strict repository scoping
        for res in results:
            assert res.chunk.repo_id == "repo-alpha-111"
            assert "auth_service.py" in res.chunk.file_path

        # 4. Generate citations
        citation_gen = CitationGenerator()
        reranked_chunks = [
            RerankedChunk(
                chunk_id=r.chunk.id,
                repo_id=r.chunk.repo_id,
                file_path=r.chunk.file_path,
                content=r.chunk.content,
                language=r.chunk.language,
                commit_hash=r.chunk.commit_hash or "HEAD",
                symbol_name=r.chunk.symbol_name,
                symbol_type=r.chunk.symbol_type,
                start_line=r.chunk.start_line,
                end_line=r.chunk.end_line,
                embedding_score=0.95,
            )
            for r in results
        ]

        citations = citation_gen.generate(
            answer="TokenValidator checks if token length exceeds 10.",
            chunks=reranked_chunks,
        )

        assert len(citations) > 0
        assert citations[0].file_path == "auth_service.py"
        assert citations[0].start_line >= 1

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
