from typing import List
import redis
from src.domain.interfaces.embedding import IEmbeddingService
from src.domain.interfaces.vector_db import IVectorDB
from src.domain.models.chunk import SemanticChunk, SearchResult
from src.application.services.ranking import RankingService

class RetrieveContextUseCase:
    def __init__(self, embedding_service: IEmbeddingService, vector_db: IVectorDB, redis_client: redis.Redis):
        self.embedding_service = embedding_service
        self.vector_db = vector_db
        self.redis_client = redis_client
        self.ranking_service = RankingService()
        self.collection_name = "codebase_chunks"

    def execute(self, query: str, repo_id: str, exact_path: str = None, top_k: int = 5) -> List[SearchResult]:
        # 1. Check Redis Cache
        cache_key = f"retrieve:{repo_id}:{query}:{exact_path}:{top_k}"
        cached = self.redis_client.get(cache_key)
        if cached:
            return [] # Simplified cache hit response
            
        # 2. Embed Query
        query_emb = self.embedding_service.generate_embedding(query)
        
        # 3. Search VectorDB with Metadata Filtering
        filter_metadata = {"repo_id": repo_id}
        raw_results = self.vector_db.search(self.collection_name, query_emb, filter_metadata, limit=top_k * 2)
        
        # 4. Map to SearchResult
        results = []
        for r in raw_results:
            chunk = SemanticChunk(
                id=r["id"],
                repo_id=r["repo_id"],
                file_path=r["file_path"],
                content=r["content"],
                language=r["language"],
                commit_hash=r["commit_hash"],
                symbol_type=r.get("symbol_type")
            )
            results.append(SearchResult(chunk=chunk, vector_score=r["score"]))
            
        # 5. Apply Ranking Heuristics
        ranked = self.ranking_service.apply_heuristics(results, exact_path=exact_path)
        final_results = ranked[:top_k]
        
        # 6. Set Cache
        self.redis_client.setex(cache_key, 3600, "cached")
        
        return final_results
