import time
import uuid
from typing import List, Callable, Optional
from sqlalchemy.orm import Session
from src.domain.interfaces.embedding import IEmbeddingService
from src.domain.interfaces.vector_db import IVectorDB
from src.domain.models.chunk import SemanticChunk
from src.infrastructure.persistence.metrics_models import DBIndexingMetrics

class IndexManager:
    def __init__(self, embedding_service: IEmbeddingService, vector_db: IVectorDB, db_session: Optional[Session] = None):
        self.embedding_service = embedding_service
        self.vector_db = vector_db
        self.db_session = db_session
        self.collection_name = "codebase_chunks"
        self.vector_db.ensure_collection(self.collection_name, self.embedding_service.dimension)

    def prepare_repository_indexing(self, repo_id: str) -> None:
        """Cleans previous repository vectors from Qdrant and ensures collection exists."""
        self.vector_db.ensure_collection(self.collection_name, self.embedding_service.dimension)
        self.vector_db.delete_by_repo(self.collection_name, repo_id)

    def index_chunk_batch(
        self,
        chunks: List[SemanticChunk],
    ) -> float:
        """
        Embeds and upserts a single small batch of chunks into Qdrant.
        Returns embedding latency in seconds.
        """
        if not chunks:
            return 0.0
        texts = [c.content for c in chunks]
        t0 = time.time()
        embeddings = self.embedding_service.generate_embeddings(texts)
        emb_latency = time.time() - t0
        self.vector_db.upsert_chunks(self.collection_name, chunks, embeddings)
        return emb_latency

    def record_indexing_metrics(
        self,
        repo_id: str,
        commit_hash: str,
        total_time_sec: float,
        chunks_count: int,
        embedding_latency_sec: float,
    ) -> None:
        """Records indexing metrics in the database if a session is available."""
        if self.db_session:
            try:
                metrics = DBIndexingMetrics(
                    id=str(uuid.uuid4()),
                    repo_id=repo_id,
                    commit_hash=commit_hash,
                    indexing_time_sec=total_time_sec,
                    chunks_created=chunks_count,
                    embedding_latency_sec=embedding_latency_sec,
                )
                self.db_session.add(metrics)
                self.db_session.commit()
            except Exception:
                # Metrics recording should not fail the overall indexing workflow
                self.db_session.rollback()

    def index_full_repository(
        self,
        repo_id: str,
        commit_hash: str,
        chunks: List[SemanticChunk],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """
        Clears previous repository vectors from Qdrant and indexes the full set of chunks.
        Supports batch processing and progress callbacks.
        """
        start_time = time.time()
        
        # 1. Clean existing repository chunks to ensure zero duplicate / orphan vectors
        self.prepare_repository_indexing(repo_id)
        
        if not chunks:
            return 0

        # 2. Batch generate embeddings & upsert using memory-safe batch size (32)
        total_chunks = len(chunks)
        batch_size = 32
        emb_time_total = 0.0

        for i in range(0, total_chunks, batch_size):
            batch = chunks[i : i + batch_size]
            emb_time_total += self.index_chunk_batch(batch)

            if progress_callback:
                progress_callback(min(i + batch_size, total_chunks), total_chunks)

        total_time = time.time() - start_time

        # 3. Save Metrics if session available
        self.record_indexing_metrics(
            repo_id=repo_id,
            commit_hash=commit_hash,
            total_time_sec=total_time,
            chunks_count=total_chunks,
            embedding_latency_sec=emb_time_total,
        )

        return total_chunks

    def process_incremental_update(
        self,
        repo_id: str,
        commit_hash: str,
        modified_files: List[str],
        deleted_files: List[str],
        new_chunks: List[SemanticChunk],
    ):
        """Processes Git diffs by deleting old files and upserting chunks from modified/new files."""
        start_time = time.time()
        
        # 1. Deletions
        for file_path in deleted_files + modified_files:
            self.vector_db.delete_by_file(self.collection_name, repo_id, file_path)
            
        # 2. Embeddings & Upserts
        emb_start = time.time()
        if new_chunks:
            texts = [c.content for c in new_chunks]
            embeddings = self.embedding_service.generate_embeddings(texts)
            self.vector_db.upsert_chunks(self.collection_name, new_chunks, embeddings)
        emb_latency = time.time() - emb_start
            
        total_time = time.time() - start_time
        
        # 3. Save Metrics
        if self.db_session:
            try:
                metrics = DBIndexingMetrics(
                    id=str(uuid.uuid4()),
                    repo_id=repo_id,
                    commit_hash=commit_hash,
                    indexing_time_sec=total_time,
                    chunks_created=len(new_chunks),
                    embedding_latency_sec=emb_latency,
                )
                self.db_session.add(metrics)
                self.db_session.commit()
            except Exception:
                self.db_session.rollback()
