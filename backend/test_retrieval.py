import os
import sys
import asyncio

# Setup paths
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.core.config import settings
from src.infrastructure.embeddings.sentence_transformer_service import SentenceTransformerService
from src.infrastructure.vector_db.qdrant_adapter import QdrantAdapter
from src.application.rag.hybrid_retriever import HybridRetriever
from src.domain.models.rag import ParsedQuery

def main():
    repo_id = "64e085e4-1305-4bd7-85a3-80d684351329"
    emb_service = SentenceTransformerService()
    vector_db = QdrantAdapter(url=settings.QDRANT_URL)
    
    retriever = HybridRetriever(emb_service, vector_db)
    pq = ParsedQuery(
        original_query="how does the auth service validate tokens?",
        rewritten_queries=["auth service token validation", "jwt verify auth_service"],
        detected_symbols=["validate_token"],
        detected_files=["src/application/services/auth_service.py"],
        repo_id=repo_id,
        intent="query"
    )
    
    async def run_retrieval():
        results = await retriever.retrieve(pq, limit=5)
        print(f"Retrieved {len(results)} chunks.")
        for r in results:
            print(f" - {r.chunk.file_path} (score: {r.vector_score:.3f}) "
                  f"sym: {r.chunk.symbol_name} ({r.chunk.symbol_type})")
                  
    asyncio.run(run_retrieval())

if __name__ == "__main__":
    main()
