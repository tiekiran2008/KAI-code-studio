"""
API Integration Tests — Memory Router
=====================================
Uses httpx.AsyncClient with dependency overrides to test the endpoints
in `src.interfaces.api.v1.memory` without standing up a real DB/Redis.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from src.main import app
from src.interfaces.api.dependencies import get_memory_service
from src.domain.memory.entities import (
    ShortTermMemory,
    MemorySearchResult,
    ConsolidationReport,
)


@pytest.fixture
def mock_svc():
    svc = MagicMock()
    # Need to mock the inner manager for some endpoints that access svc._mgr directly
    mgr = AsyncMock()
    svc._mgr = mgr
    return svc


@pytest.fixture
def api_client(mock_svc):
    app.dependency_overrides[get_memory_service] = lambda: mock_svc
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_search_memories_unauthorized(api_client):
    # No X-User-ID header
    response = await api_client.post("/api/v1/memory/search", json={"query": "test"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_memories_success(api_client, mock_svc):
    mem = ShortTermMemory(id="m1", user_id="u1", content="test")
    mock_svc.search = AsyncMock(return_value=[MemorySearchResult(memory=mem, relevance_score=0.9)])
    
    response = await api_client.post(
        "/api/v1/memory/search", 
        json={"query": "test", "top_k": 5},
        headers={"X-User-ID": "u1"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["memory"]["id"] == "m1"
    assert data["results"][0]["relevance_score"] == 0.9


@pytest.mark.asyncio
async def test_forget_memory_soft(api_client, mock_svc):
    mock_svc.forget_memory = AsyncMock()
    
    response = await api_client.delete(
        "/api/v1/memory/m1",
        headers={"X-User-ID": "u1"}
    )
    
    assert response.status_code == 200
    mock_svc.forget_memory.assert_called_once_with("m1", "u1", hard=False)


@pytest.mark.asyncio
async def test_forget_user_all(api_client, mock_svc):
    mock_svc.forget_user = AsyncMock(return_value=42)
    
    response = await api_client.delete(
        "/api/v1/memory/users/u1/all",
        headers={"X-User-ID": "u1"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_deleted"] == 42


@pytest.mark.asyncio
async def test_consolidate_trigger(api_client, mock_svc):
    report = ConsolidationReport(memories_scanned=10, memories_merged=2)
    mock_svc._mgr.consolidate.return_value = report
    
    response = await api_client.post(
        "/api/v1/memory/consolidate",
        headers={"X-User-ID": "admin"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["memories_scanned"] == 10
    assert data["memories_merged"] == 2
