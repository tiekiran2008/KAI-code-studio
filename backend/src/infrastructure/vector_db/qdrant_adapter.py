import uuid
from typing import List, Dict, Any, Optional
from qdrant_client.http import models as rest
from src.infrastructure.vector_db.qdrant_client_factory import get_shared_qdrant_client
from src.domain.interfaces.vector_db import IVectorDB
from src.domain.models.chunk import SemanticChunk

class QdrantAdapter(IVectorDB):
    def __init__(self, url: str = "http://localhost:6333"):
        self.client = get_shared_qdrant_client(url)
        
    def ensure_collection(self, collection_name: str, vector_size: int):
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
