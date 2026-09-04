"""Unit tests for Evaluation Agent confidence evaluation and retry controls."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.agents.evaluation import EvaluationAgent
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.rag import LLMResponse

@pytest.mark.asyncio
async def test_evaluation_agent_passing():
    mock_llm = MagicMock(spec=ILLMProvider)
    eval_json = """{
        "confidence_score": 0.92,
        "groundedness_ratio": 0.95,
        "is_passed": true,
        "notes": "Outputs are accurate and grounded."
    }"""
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content=eval_json, prompt_tokens=50, completion_tokens=50, total_tokens=100, model_name="test"
    ))

    evaluator = EvaluationAgent(mock_llm)
    state = {
        "query": "Explain authentication",
        "retrieved_context": "def login(): pass",
        "agent_outputs": {"code_analysis": {"summary": "login function"}},
        "retry_count": 0
    }
    
    result = await evaluator.execute(state)
    
    assert result["confidence_score"] == 0.92
    assert result["is_eval_passed"] is True
    assert result["next_agent"] == "supervisor"

@pytest.mark.asyncio
async def test_evaluation_agent_failing_triggers_retry():
    mock_llm = MagicMock(spec=ILLMProvider)
    eval_json = """{
        "confidence_score": 0.20,
        "groundedness_ratio": 0.20,
        "is_passed": false,
        "notes": "Ungrounded output."
    }"""
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content=eval_json, prompt_tokens=50, completion_tokens=50, total_tokens=100, model_name="test"
    ))

    evaluator = EvaluationAgent(mock_llm)
    state = {
        "query": "Explain authentication",
        "retrieved_context": "",
        "agent_outputs": {},
        "retry_count": 0
    }
    
    result = await evaluator.execute(state)
    
    assert result["confidence_score"] == 0.20
    assert result["is_eval_passed"] is False
    assert result["retry_count"] == 1
    assert result["next_agent"] == "context"
