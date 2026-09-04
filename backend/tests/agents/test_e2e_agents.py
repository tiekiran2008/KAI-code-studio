"""End-to-End API integration test for the /api/v1/agents/execute endpoint."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from src.main import app
from src.interfaces.api.dependencies import get_agent_use_case
from src.application.use_cases.agent_execution import ExecuteAgentWorkflowUseCase

@pytest.mark.asyncio
async def test_e2e_agent_execute_endpoint():
    mock_workflow_response = {
        "answer": "Consolidated multi-agent code analysis report.",
        "plan": {"summary": "Execution plan", "selected_agents": ["context", "code_analysis"]},
        "agent_outputs": {
            "code_analysis": {
                "summary": "Completed analysis",
                "details": "Class AuthHandler follows the Repository pattern.",
                "data": {}
            }
        },
        "citations": [{"file_path": "src/auth.py", "confidence": 0.95}],
        "confidence_score": 0.90,
        "groundedness_ratio": 0.92,
        "execution_trace": [{"agent": "supervisor", "action": "synthesized_final_answer"}],
        "latency_ms": 150.0,
        "session_id": "test_agent_session",
        "repo_id": "test_repo_id",
        "error": None
    }

    mock_use_case = MagicMock(spec=ExecuteAgentWorkflowUseCase)
    mock_use_case.execute = AsyncMock(return_value=mock_workflow_response)

    app.dependency_overrides[get_agent_use_case] = lambda: mock_use_case

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "query": "Analyze code architecture and check for bugs",
            "repo_id": "test_repo_id"
        }
        response = await ac.post("/api/v1/agents/execute", json=payload)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["answer"] == "Consolidated multi-agent code analysis report."
        assert json_data["confidence_score"] == 0.90
        assert "code_analysis" in json_data["agent_outputs"]

    app.dependency_overrides.clear()
