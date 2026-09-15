import uuid
from typing import List, Dict, Any, Optional, Set
from qdrant_client.http import models as rest
from src.infrastructure.vector_db.qdrant_client_factory import get_shared_qdrant_client
from src.domain.interfaces.vector_db import IVectorDB
from src.domain.models.chunk import SemanticChunk

from src.core.config import settings

class QdrantAdapter(IVectorDB):
    _ensured_collections = set()

    def __init__(self, url: str = "", api_key: Optional[str] = None):
        q_url = url or settings.QDRANT_URL
        q_api_key = api_key if api_key is not None else (settings.QDRANT_API_KEY or None)
        self.client = get_shared_qdrant_client(q_url, api_key=q_api_key)
        
    def ensure_collection(self, collection_name: str, vector_size: int):
        if collection_name in QdrantAdapter._ensured_collections:
            return

        try:
            collections = self.client.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=rest.VectorParams(
                        size=vector_size,
                        distance=rest.Distance.COSINE
                    )
                )
                # Create payload index for repo_id to accelerate filtered multi-tenant queries
                try:
                    self.client.create_payload_index(
                        collection_name=collection_name,
                        field_name="repo_id",
                        field_schema=rest.PayloadSchemaType.KEYWORD
                    )
                except Exception:
                    pass
            QdrantAdapter._ensured_collections.add(collection_name)
        except Exception:
            # Do not crash caller if Qdrant is temporarily busy
            pass

    def upsert_chunks(self, collection_name: str, chunks: List[SemanticChunk], embeddings: List[List[float]]):
        points = []
        for chunk, emb in zip(chunks, embeddings):
            points.append(rest.PointStruct(
                id=chunk.id,
                vector=emb,
                payload={
                    "repo_id": chunk.repo_id,
                    "file_path": chunk.file_path,
                    "content": chunk.content,
                    "language": chunk.language,
                    "commit_hash": chunk.commit_hash,
                    "symbol_name": chunk.symbol_name,
                    "symbol_type": chunk.symbol_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line
                }
            ))
        if points:
            # Upsert in batches of 100 for network efficiency
            batch_size = 100
            for i in range(0, len(points), batch_size):
                self.client.upsert(collection_name=collection_name, points=points[i : i + batch_size])

    def delete_by_file(self, collection_name: str, repo_id: str, file_path: str):
        self.client.delete(
            collection_name=collection_name,
            points_selector=rest.Filter(
                must=[
                    rest.FieldCondition(key="repo_id", match=rest.MatchValue(value=repo_id)),
                    rest.FieldCondition(key="file_path", match=rest.MatchValue(value=file_path))
                ]
            )
        )

    def delete_by_repo(self, collection_name: str, repo_id: str):
        """Delete all points belonging to a specific repository."""
        self.client.delete(
            collection_name=collection_name,
            points_selector=rest.Filter(
                must=[
                    rest.FieldCondition(key="repo_id", match=rest.MatchValue(value=repo_id))
                ]
            )
        )

    def search(self, collection_name: str, query_embedding: List[float], filter_metadata: Dict[str, Any] = None, limit: int = 10) -> List[Dict[str, Any]]:
        query_filter = None
        if filter_metadata:
            must_conditions = [
                rest.FieldCondition(key=k, match=rest.MatchValue(value=v))
                for k, v in filter_metadata.items()
            ]
            query_filter = rest.Filter(must=must_conditions)
            
        # Use high-level query_points method to support local and remote Qdrant clients
        search_response = self.client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            query_filter=query_filter,
            limit=limit,
            with_payload=True
        )
        
        results = []
        for scored_point in search_response.points:
            res = scored_point.payload.copy() if scored_point.payload else {}
            res["score"] = scored_point.score
            res["id"] = str(scored_point.id)
            results.append(res)
        return results

    def get_indexed_files(self, collection_name: str, repo_id: str) -> Set[str]:
        """
        Return the set of distinct file_path values indexed for the given repo_id.
        Uses Qdrant scroll to page through all matching points without loading vectors.
        This is used as a fallback to reconstruct the file tree when the local clone
        directory no longer exists (e.g. after an ephemeral Render restart).
        """
        file_paths: Set[str] = set()
        try:
            scroll_filter = rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="repo_id",
                        match=rest.MatchValue(value=repo_id),
                    )
                ]
            )
            offset = None
            while True:
                results, next_offset = self.client.scroll(
                    collection_name=collection_name,
                    scroll_filter=scroll_filter,
                    limit=250,
                    offset=offset,
                    with_payload=["file_path"],
                    with_vectors=False,
                )
                for point in results:
                    if point.payload and point.payload.get("file_path"):
                        file_paths.add(point.payload["file_path"])
                if next_offset is None:
                    break
                offset = next_offset
        except Exception:
            # Do not crash caller if Qdrant is temporarily unavailable
            pass
        return file_paths

