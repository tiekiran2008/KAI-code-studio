import os
import sys
import uuid
import asyncio

# Setup paths
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from src.core.config import settings
from src.interfaces.api.dependencies import _get_session_factory
from src.infrastructure.embeddings.sentence_transformer_service import SentenceTransformerService
from src.infrastructure.vector_db.qdrant_adapter import QdrantAdapter
from src.application.services.index_manager import IndexManager
from src.domain.models.chunk import SemanticChunk
from src.infrastructure.parsing.python_parser import PythonParser

def main():
    print(f"GEMINI_API_KEY is set: {bool(settings.GEMINI_API_KEY)}")
    print(f"OPENAI_API_KEY is set: {bool(settings.OPENAI_API_KEY)}")
    
    repo_id = "64e085e4-1305-4bd7-85a3-80d684351329"
    src_dir = os.path.abspath("src")
    
    print(f"Initializing indexing for repo: {repo_id}")
    
    # 1. Setup DB Session
    session_factory = _get_session_factory()
    db_session = session_factory()
    
    # Ensure tables exist
    from src.infrastructure.persistence.base import Base
    from src.infrastructure.persistence.metrics_models import DBIndexingMetrics
    from sqlalchemy import create_engine
    engine = create_engine(settings.POSTGRES_URL)
    Base.metadata.create_all(bind=engine)
    
    # 2. Setup IndexManager
    emb_service = SentenceTransformerService()
    vector_db = QdrantAdapter(url=settings.QDRANT_URL)
    index_manager = IndexManager(emb_service, vector_db, db_session)
    
    # 3. Collect Python files
    python_files = []
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith(".py"):
                python_files.append(os.path.join(root, f))
                
    parser = PythonParser()
    new_chunks = []
    
    # 4. Generate Chunks
    print(f"Found {len(python_files)} python files. Parsing...")
    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Use forward slashes for cross-platform consistency in vector DB
            rel_path = os.path.relpath(file_path, start=os.path.abspath(".")).replace("\\", "/")
            
            # Add file-level chunk
            # Limiting content to first 8000 characters to prevent embedding token limit issues
            file_chunk_content = content[:8000]
            if file_chunk_content.strip():
                new_chunks.append(SemanticChunk(
                    id=str(uuid.uuid4()),
                    repo_id=repo_id,
                    file_path=rel_path,
                    content=file_chunk_content,
                    language="python",
                    commit_hash="local_test"
                ))
            
            # Add symbol-level chunks
            symbols = parser.parse_symbols(content, file_path)
            lines = content.split('\n')
            for sym in symbols:
                if sym.start_line and sym.end_line:
                    sym_content = '\n'.join(lines[sym.start_line-1:sym.end_line])
                    if sym_content.strip():
                        new_chunks.append(SemanticChunk(
                            id=str(uuid.uuid4()),
                            repo_id=repo_id,
                            file_path=rel_path,
                            content=sym_content[:8000],
                            language="python",
                            commit_hash="local_test",
                            symbol_name=sym.name,
                            symbol_type=sym.symbol_type,
                            start_line=sym.start_line,
                            end_line=sym.end_line
                        ))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
    # 5. Process Update
    print(f"Pushing {len(new_chunks)} chunks to Qdrant (this takes a moment)...")
    index_manager.process_incremental_update(
        repo_id=repo_id,
        commit_hash="local_test",
        modified_files=[],
        deleted_files=[],
        new_chunks=new_chunks
    )
    print("Indexing complete.")
    
    # Verify
    print("Verifying in Qdrant...")
    from qdrant_client.http import models as rest
    
    result = vector_db.client.count(
        collection_name="codebase_chunks",
        count_filter=None
    )
    print(f"Total chunks in 'codebase_chunks' collection: {result.count}")
    
    filtered_result = vector_db.client.count(
        collection_name="codebase_chunks",
        count_filter=rest.Filter(
            must=[rest.FieldCondition(key="repo_id", match=rest.MatchValue(value=repo_id))]
        )
    )
    print(f"Total chunks for repo {repo_id}: {filtered_result.count}")
    
    # Run a test retrieval using HybridRetriever
    print("\nRunning semantic retrieval test...")
    from src.application.rag.hybrid_retriever import HybridRetriever
    from src.domain.models.rag import ParsedQuery
    
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
