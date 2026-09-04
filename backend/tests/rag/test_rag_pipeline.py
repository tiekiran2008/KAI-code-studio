"""Integration tests for the RAG pipeline."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.rag.query_processor import QueryProcessor
from src.domain.interfaces.llm import ILLMProvider
from src.domain.interfaces.embedding import IEmbeddingService
from src.domain.interfaces.vector_db import IVectorDB
from src.domain.models.rag import LLMResponse
import redis

@pytest.mark.asyncio
async def test_full_pipeline_orchestration():
    # Mock LLM
    mock_llm = MagicMock(spec=ILLMProvider)
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content="The validate_token function handles token validation. [FILE: src/auth.py, LINES: 1-10]",
        prompt_tokens=100, completion_tokens=50, total_tokens=150, model_name="test-model"
    ))
    
    # Mock Embeddings
    mock_emb = MagicMock(spec=IEmbeddingService)
    mock_emb.generate_embedding = MagicMock(return_value=[0.1] * 384)
    
    # Mock VectorDB
    mock_vdb = MagicMock(spec=IVectorDB)
    mock_vdb.search = MagicMock(return_value=[{
        "id": "c1",
        "repo_id": "r1",
        "file_path": "src/auth.py",
        "content": "def validate_token(token): pass",
        "language": "python",
        "commit_hash": "hash",
        "symbol_name": "validate_token",
        "symbol_type": "function",
        "start_line": 1,
        "end_line": 10,
        "score": 0.9
    }])
    
    # Mock Redis client
    mock_redis = MagicMock(spec=redis.Redis)
    mock_redis.get = MagicMock(return_value=None)
    mock_redis.setex = MagicMock(return_value=True)
    
    # Instantiate pipeline processor
    qp = QueryProcessor(mock_llm, mock_emb, mock_vdb, mock_redis)
    
    resp = await qp.process("where is authentication token validated?", "r1", session_id="test_session")
    
    assert resp.answer == "The validate_token function handles token validation. [FILE: src/auth.py, LINES: 1-10]"
    assert resp.intent.value == "security_review"  # Classified by query understanding
    assert len(resp.citations) > 0
    assert resp.citations[0].file_path == "src/auth.py"
