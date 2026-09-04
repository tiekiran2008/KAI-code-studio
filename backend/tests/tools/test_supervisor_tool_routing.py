"""
Integration Tests — Supervisor Tool Routing
===========================================
Tests that the SupervisorAgent correctly receives tool calls from the LLM,
executes them via the ToolManager, and updates its state.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.application.agents.supervisor import SupervisorAgent
from src.domain.models.agents import AgentType
from src.domain.models.tools import ToolResult


@pytest.fixture
def mock_llm():
    return AsyncMock()

@pytest.fixture
def mock_tool_manager():
    return AsyncMock()

@pytest.fixture
def supervisor(mock_llm, mock_tool_manager):
    return SupervisorAgent(llm_provider=mock_llm, tool_manager=mock_tool_manager)


@pytest.mark.asyncio
async def test_supervisor_synthesizes_when_no_tool_calls(supervisor, mock_llm, mock_tool_manager):
    mock_resp = MagicMock()
    mock_resp.content = "Final synthesis."
    mock_resp.tool_calls = []  # No tool calls
    mock_llm.complete.return_value = mock_resp

    state = {
        "query": "How does auth work?",
        "plan": {"selected_agents": ["context"]},
        "agent_outputs": {"context": {"summary": "Auth uses JWT"}},
        "tool_results": []
    }

    result = await supervisor.execute(state)
    
    assert result["next_agent"] == "__end__"
    assert result["final_answer"] == "Final synthesis."
    mock_tool_manager.execute_tool.assert_not_called()


@pytest.mark.asyncio
async def test_supervisor_executes_tools_and_loops(supervisor, mock_llm, mock_tool_manager):
    # LLM requests a tool call
    mock_resp = MagicMock()
    mock_resp.content = "Let me check the database."
    mock_resp.tool_calls = [
        {"name": "database_read", "arguments": {"action": "repo_metadata", "user_id": "u1"}}
    ]
    mock_llm.complete.return_value = mock_resp

    # ToolManager returns a successful result
    mock_tool_manager.execute_tool.return_value = ToolResult(success=True, data={"summary": "React App"})

    state = {
        "query": "What is the tech stack?",
        "plan": {"selected_agents": ["context"]},
        "agent_outputs": {},
        "tool_results": []
    }

    result = await supervisor.execute(state)
    
    # Should route back to itself to synthesize the result
    assert result["next_agent"] == AgentType.SUPERVISOR.value
    
    # Verify tool results were appended
    assert len(result["tool_results"]) == 1
    assert result["tool_results"][0]["tool_name"] == "database_read"
    assert result["tool_results"][0]["data"] == {"summary": "React App"}
    
    # Verify manager was called
    mock_tool_manager.execute_tool.assert_called_once()
