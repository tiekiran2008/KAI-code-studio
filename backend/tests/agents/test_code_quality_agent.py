"""
Unit tests for AI Architecture & Code Quality Agent (Phase 11.5)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.agents.code_quality import CodeQualityAgent
from src.domain.models.agents import AgentType, AgentState


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.complete = AsyncMock()
    json_payload = """{
        "findings": [
            {
                "category": "clean_architecture",
                "severity": "high",
                "priority": "high",
                "file_path": "src/domain/user.py",
                "line_number": 12,
                "explanation": "Domain layer directly imports infrastructure persistence module.",
                "root_cause": "Tightly coupled domain model with SQLAlchemy.",
                "business_impact": "Prevents switching database drivers or isolation testing.",
                "recommendation": "Use abstract repository interface in domain layer.",
                "estimated_effort_hours": 3.0,
                "confidence_score": 0.95
            }
        ],
        "metrics": {
            "overall_health_score": 85.0,
            "architecture_score": 80.0,
            "maintainability_score": 88.0,
            "technical_debt_score": 75.0,
            "complexity_score": 90.0,
            "documentation_score": 82.0,
            "modularity_score": 84.0,
            "testability_score": 86.0
        },
        "dependency_analysis": {
            "layer_violations": [
                {
                    "source_layer": "domain",
                    "target_layer": "infrastructure",
                    "source_file": "src/domain/user.py",
                    "target_file": "src/infrastructure/db.py",
                    "description": "Domain entity imports infrastructure db"
                }
            ],
            "circular_dependencies": [],
            "hotspot_files": [
                {
                    "file_path": "src/domain/user.py",
                    "complexity_score": 78.0,
                    "technical_debt_hours": 3.0,
                    "issue_count": 1
                }
            ]
        },
        "summary": "Clean Architecture compliance issues found in domain layer."
    }"""
    llm.complete.return_value = MagicMock(content=json_payload)
    return llm


@pytest.mark.asyncio
async def test_code_quality_agent_execution(mock_llm):
    agent = CodeQualityAgent(mock_llm)
    state: AgentState = {
        "query": "Evaluate architecture quality and Clean Architecture compliance",
        "retrieved_context": "class User(Base):\n    __tablename__ = 'users'",
        "pending_tasks": [AgentType.CODE_QUALITY.value],
        "completed_tasks": [],
        "agent_outputs": {},
    }

    result = await agent.execute(state)

    assert AgentType.CODE_QUALITY.value in result["agent_outputs"]
    output = result["agent_outputs"][AgentType.CODE_QUALITY.value]
    assert len(output["structured_findings"]) == 1
    assert output["structured_findings"][0]["category"] == "clean_architecture"
    assert output["metrics"]["overall_health_score"] == 85.0
    assert len(output["dependency_analysis"]["layer_violations"]) == 1
    assert AgentType.CODE_QUALITY.value in result["completed_tasks"]


@pytest.mark.asyncio
async def test_code_quality_agent_handles_invalid_json(mock_llm):
    mock_llm.complete.return_value = MagicMock(content="Non-JSON raw LLM text")
    agent = CodeQualityAgent(mock_llm)
    state: AgentState = {
        "query": "Evaluate architecture",
        "retrieved_context": "def foo(): pass",
        "pending_tasks": [AgentType.CODE_QUALITY.value],
        "completed_tasks": [],
        "agent_outputs": {},
    }

    result = await agent.execute(state)

    output = result["agent_outputs"][AgentType.CODE_QUALITY.value]
    assert output["structured_findings"] == []
    assert output["metrics"] == {}
