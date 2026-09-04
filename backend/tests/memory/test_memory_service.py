"""
Unit Tests — Memory Service
===========================
Tests the application layer façade that delegates to the MemoryManager.
"""
import pytest
from unittest.mock import AsyncMock

from src.application.services.memory_service import MemoryService
from src.domain.memory.entities import (
    EpisodicMemory,
    EpisodeType,
    LongTermMemory,
    MemoryType,
    MemorySearchResult,
)


@pytest.fixture
def mock_manager():
    return AsyncMock()

@pytest.fixture
def service(mock_manager):
    return MemoryService(mock_manager)


@pytest.mark.asyncio
async def test_enrich_agent_context(service, mock_manager):
    mock_manager.enrich_context.return_value = "enriched context"
    result = await service.enrich_agent_context(
        query="test",
        user_id="u1",
        session_id="s1",
        repository_id="r1",
        existing_rag_context="",
        token_budget=1000
    )
    assert result == "enriched context"
    mock_manager.enrich_context.assert_called_once()


@pytest.mark.asyncio
async def test_save_episode_infers_type_from_outputs(service, mock_manager):
    await service.save_episode(
        user_id="u1",
        session_id="s1",
        query="fix bug",
        repository_id="r1",
        agent_outputs={"bug_detection": {}},
        final_answer="fixed",
        confidence_score=0.9,
        citations=[],
        execution_trace=[]
    )
    
    # Check that MemoryManager was called with an EpisodicMemory 
    # where the episode_type was correctly inferred as DEBUGGING
    call_args = mock_manager.create_episodic.call_args[0]
    mem = call_args[1]
    assert isinstance(mem, EpisodicMemory)
    assert mem.episode_type == EpisodeType.DEBUGGING


@pytest.mark.asyncio
async def test_update_user_preferences_creates_new(service, mock_manager):
    mock_manager.search.return_value = []
    mock_manager.create_long_term.return_value = LongTermMemory()
    
    await service.update_user_preferences("u1", {"preferred_languages": ["python"]})
    
    mock_manager.create_long_term.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_preferences_merges_existing(service, mock_manager):
    existing = LongTermMemory(id="l1", user_id="u1")
    mock_manager.search.return_value = [MemorySearchResult(memory=existing)]
    mock_manager.update_memory.return_value = existing
    
    await service.update_user_preferences("u1", {"preferred_languages": ["python"]})
    
    mock_manager.update_memory.assert_called_once()
    assert "python" in existing.preferences.preferred_languages


def test_distil_lessons():
    outputs = {"bug_detection": {}, "code_analysis": {}}
    answer = "The issue was a null pointer."
    lesson = MemoryService._distil_lessons(outputs, answer)
    assert "2 agent" in lesson
    assert "null pointer" in lesson
