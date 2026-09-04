"""Unit tests for Planner Agent decomposition logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.agents.planner import PlannerAgent
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.rag import LLMResponse

@pytest.mark.asyncio
async def test_planner_agent_json_parsing():
    mock_llm = MagicMock(spec=ILLMProvider)
    json_plan = """```json
    {
        "summary": "Plan to analyze code and audit bugs",
        "selected_agents": ["context", "code_analysis", "bug_detection"],
        "parallel_groups": [["context"], ["code_analysis", "bug_detection"]]
    }
    ```"""
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content=json_plan, prompt_tokens=50, completion_tokens=50, total_tokens=100, model_name="test"
    ))

    planner = PlannerAgent(mock_llm)
    state = {"query": "Check for bugs in the authentication middleware"}
    
    result = await planner.execute(state)
    
    assert "plan" in result
    assert result["plan"]["selected_agents"] == ["context", "code_analysis", "bug_detection"]
    assert result["next_agent"] == "context"

@pytest.mark.asyncio
async def test_planner_agent_fallback():
    mock_llm = MagicMock(spec=ILLMProvider)
    # Return invalid non-JSON string to test fallback
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content="Invalid response format", prompt_tokens=50, completion_tokens=50, total_tokens=100, model_name="test"
    ))

    planner = PlannerAgent(mock_llm)
    state = {"query": "Find security bugs and optimize slow database queries"}
    
    result = await planner.execute(state)
    
    assert "plan" in result
    selected = result["plan"]["selected_agents"]
    assert "context" in selected
    assert "security_review" in selected
    assert "performance" in selected
