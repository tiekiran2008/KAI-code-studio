"""
Unit Tests — Database Tool Adapter
===================================
Tests DatabaseToolAdapter actions (memory_search, conversation_history, repo_metadata),
permission metadata, and error handling with mocked MemoryService.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.tools.adapters.database import DatabaseToolAdapter
from src.domain.models.tools import PermissionLevel
from src.domain.memory.entities import MemoryType


@pytest.fixture
def mock_memory_service():
    service = MagicMock()
    
    # Mock search result
    mock_memory_entity = MagicMock()
    mock_memory_entity.id = "mem-1"
    mock_memory_entity.memory_type = MemoryType.LONG_TERM
    mock_memory_entity.content = "User prefers Clean Architecture with FastAPI"
    
    mock_search_result = MagicMock()
    mock_search_result.memory = mock_memory_entity
    
    service.search = AsyncMock(return_value=[mock_search_result])

    # Mock get_memory for session
    mock_session = MagicMock()
    mock_session.memory_type = MemoryType.SHORT_TERM
    mock_session.conversation_turns = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    service.get_memory = AsyncMock(return_value=mock_session)
    
    return service


@pytest.fixture
def db_adapter(mock_memory_service):
    return DatabaseToolAdapter(memory_service=mock_memory_service)


def test_db_adapter_metadata(db_adapter):
    metadata = db_adapter.get_metadata()
    assert metadata.name == "database_read"
    assert metadata.permissions == PermissionLevel.RESTRICTED
    assert "action" in metadata.input_schema["properties"]
    assert "user_id" in metadata.input_schema["properties"]


@pytest.mark.asyncio
async def test_db_adapter_memory_search(db_adapter, mock_memory_service):
    result = await db_adapter.execute(
        action="memory_search",
        user_id="user-123",
        repo_id="repo-456",
        query="architecture preferences",
    )
    assert result.success is True
    assert len(result.data["results"]) == 1
    assert result.data["results"][0]["content"] == "User prefers Clean Architecture with FastAPI"
    mock_memory_service.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_db_adapter_conversation_history(db_adapter, mock_memory_service):
    result = await db_adapter.execute(
        action="conversation_history",
        user_id="user-123",
        session_id="session-789",
    )
    assert result.success is True
    assert len(result.data["history"]) == 2
    mock_memory_service.get_memory.assert_awaited_once_with("session-789", "user-123")


@pytest.mark.asyncio
async def test_db_adapter_repo_metadata(db_adapter, mock_memory_service):
    mock_repo_mem = MagicMock()
    mock_repo_mem.content = "FastAPI + React Monorepo"
    mock_repo_mem.tech_stack = ["Python", "TypeScript", "React", "PostgreSQL"]
    
    mock_search_res = MagicMock()
    mock_search_res.memory = mock_repo_mem
    mock_memory_service.search = AsyncMock(return_value=[mock_search_res])

    result = await db_adapter.execute(
        action="repo_metadata",
        user_id="user-123",
        repo_id="repo-456",
    )
    assert result.success is True
    assert result.data["summary"] == "FastAPI + React Monorepo"
    assert "Python" in result.data["tech_stack"]


@pytest.mark.asyncio
async def test_db_adapter_invalid_action(db_adapter):
    result = await db_adapter.execute(
        action="invalid_action",
        user_id="user-123",
    )
    assert result.success is False
    assert "Unknown action" in result.error
