"""
Unit tests for RefactoringAnalysisAgent
========================================
Tests execution, context aggregation, JSON parsing, and fallback handling.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.agents.refactoring import RefactoringAnalysisAgent
from src.domain.models.agents import AgentType, AgentState


@pytest.mark.asyncio
async def test_refactoring_agent_execution_success():
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock()
    mock_llm.complete.return_value = MagicMock(
        content='''
        {
          "findings": [
            {
              "refactoring_type": "Extract Method",
              "priority": "high",
              "category": "complexity",
              "file_path": "src/services.py",
              "line_number": 45,
              "explanation": "Extract complex logic from process_data method",
              "current_problem": "Method exceeds 80 lines",
              "suggested_refactoring": "Extract helper functions",
              "before_preview": "def process_data(): ...",
              "after_preview": "def process_data(): helper()",
              "benefits": ["Better readability", "Lower cyclomatic complexity"],
              "risks": ["Updating caller signatures"],
              "estimated_effort_hours": 2.5,
              "confidence_score": 0.94
            }
          ],
          "overall_priority": "high",
          "estimated_total_effort_hours": 2.5,
          "estimated_maintainability_improvement": 30.0,
          "estimated_technical_debt_reduction": 4.0,
          "estimated_complexity_reduction": 25.0,
          "summary": "Found 1 refactoring opportunity"
        }
        '''
    )

    agent = RefactoringAnalysisAgent(mock_llm)
    state: AgentState = {
        "query": "Analyze codebase for refactoring",
        "retrieved_context": "def process_data(): pass",
        "agent_outputs": {
            "code_review": {
                "structured_findings": [{"issue": "Long function", "severity": "high"}]
            }
        },
        "pending_tasks": [AgentType.REFACTORING_ANALYSIS.value],
        "completed_tasks": [],
        "execution_trace": [],
    }

    result = await agent.execute(state)

    assert AgentType.REFACTORING_ANALYSIS.value in result["agent_outputs"]
    output = result["agent_outputs"][AgentType.REFACTORING_ANALYSIS.value]
    assert len(output["structured_findings"]) == 1
    assert output["structured_findings"][0]["refactoring_type"] == "Extract Method"
    assert output["estimated_maintainability_improvement"] == 30.0
    assert output["estimated_technical_debt_reduction"] == 4.0
    assert output["estimated_complexity_reduction"] == 25.0


@pytest.mark.asyncio
async def test_refactoring_agent_invalid_json_fallback():
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock()
    mock_llm.complete.return_value = MagicMock(content="Invalid non-json output from LLM")

    agent = RefactoringAnalysisAgent(mock_llm)
    state: AgentState = {
        "query": "Check code smells",
        "retrieved_context": "",
        "agent_outputs": {},
        "pending_tasks": [AgentType.REFACTORING_ANALYSIS.value],
        "completed_tasks": [],
    }

    result = await agent.execute(state)
    output = result["agent_outputs"][AgentType.REFACTORING_ANALYSIS.value]
    assert output["structured_findings"] == []
    assert output["overall_priority"] == "medium"
