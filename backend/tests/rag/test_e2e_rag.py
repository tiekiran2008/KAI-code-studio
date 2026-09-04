"""End-to-End API test for the RAG endpoint."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from src.main import app
from src.interfaces.api.dependencies import get_rag_use_case, get_conversation_manager
from src.application.use_cases.rag_query import RAGQueryUseCase
from src.application.rag.conversation_manager import ConversationManager
from src.domain.models.rag import RAGResponse, TokenUsage, QueryIntent, ValidationResult

@pytest.mark.asyncio
async def test_e2e_rag_query_endpoint():
    # Setup mock RAG response
    mock_response = RAGResponse(
        answer="Authentication works via JWT tokens.",
        citations=[],
        confidence=0.9,
        intent=QueryIntent.EXPLAIN_CODE,
        session_id="test_session_id",
        repo_id="test_repo_id",
        latency_ms=120.0,
        token_usage=TokenUsage(100, 50, 150),
        retrieved_chunk_count=2,
        is_cached=False,
        validation=ValidationResult(True, 0.9, 2, 2)
    )
    
    # Mock use case
    mock_use_case = MagicMock(spec=RAGQueryUseCase)
    mock_use_case.execute = AsyncMock(return_value=mock_response)
    
    # Override FastAPI dependency registry
    app.dependency_overrides[get_rag_use_case] = lambda: mock_use_case
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "question": "How does authentication work?",
            "repo_id": "test_repo_id"
        }
        response = await ac.post("/api/v1/rag/query", json=payload)
        
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["answer"] == "Authentication works via JWT tokens."
        assert json_data["intent"] == "explain_code"
        assert json_data["session_id"] == "test_session_id"
        
    app.dependency_overrides.clear()
