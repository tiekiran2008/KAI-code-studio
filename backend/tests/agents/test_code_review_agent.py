"""
Regression tests for CodeReviewAgent.

These tests specifically verify the fix for the confirmed bug:
    NameError: name 'query' is not defined

Root cause: CodeReviewAgent.execute() used `query` and `context` in the
prompt f-string without ever retrieving them from `state`.
The fix adds:
    query   = state.get("query", "")
    context = state.get("retrieved_context", "")

The tests below MUST exercise the real execute() code path so that
if the retrieval lines are ever removed again, the tests will fail with
a NameError rather than silently passing.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.application.agents.code_review import CodeReviewAgent
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.rag import LLMResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm(content: str) -> ILLMProvider:
    """Return a mock LLM that returns the given content string."""
    mock_llm = MagicMock(spec=ILLMProvider)
    mock_llm.complete = AsyncMock(
        return_value=LLMResponse(
            content=content,
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150,
            model_name="test-model",
        )
    )
    return mock_llm


# ---------------------------------------------------------------------------
# Regression test – the exact failing path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_code_review_agent_does_not_raise_name_error_for_query():
    """
    REGRESSION: Before the fix, CodeReviewAgent.execute() raised
        NameError: name 'query' is not defined
    because `query` and `context` were used in the f-string prompt
    without being retrieved from state.

    This test calls execute() with a realistic state and asserts that:
    1. No NameError (or any other exception) is raised.
    2. The returned dict contains the expected keys.
    """
    llm = _make_llm("[]")
    agent = CodeReviewAgent(llm)

    state = {
        "query": "Review the authentication module for SOLID violations",
        "retrieved_context": "def login(user, pwd):\n    return db.check(user, pwd)\n",
        "review_config": {"strictness": "high"},
        "pending_tasks": ["code_review", "evaluation"],
        "completed_tasks": [],
    }

    # Must not raise NameError
    result = await agent.execute(state)

    assert "agent_outputs" in result
    assert "code_review" in result["agent_outputs"]
    assert "pending_tasks" in result
    assert "code_review" not in result["pending_tasks"]
    assert "code_review" in result["completed_tasks"]


@pytest.mark.asyncio
async def test_code_review_agent_query_propagated_into_prompt():
    """
    Verify that the user's query text is actually forwarded to the LLM.
    This proves state.get("query") is executed, not just that the line exists.
    """
    captured_prompts: list = []

    async def capturing_complete(prompt, **kwargs):
        captured_prompts.append(prompt)
        return LLMResponse(
            content="[]",
            prompt_tokens=50,
            completion_tokens=10,
            total_tokens=60,
            model_name="test-model",
        )

    mock_llm = MagicMock(spec=ILLMProvider)
    mock_llm.complete = capturing_complete

    agent = CodeReviewAgent(mock_llm)

    unique_query = "UNIQUE_QUERY_STRING_FOR_PROPAGATION_TEST"
    state = {
        "query": unique_query,
        "retrieved_context": "class Foo: pass",
        "review_config": {},
        "pending_tasks": ["code_review"],
        "completed_tasks": [],
    }

    await agent.execute(state)

    assert len(captured_prompts) == 1
    assert unique_query in captured_prompts[0], (
        f"Expected the query to appear in the LLM prompt but got:\n{captured_prompts[0]}"
    )


@pytest.mark.asyncio
async def test_code_review_agent_context_propagated_into_prompt():
    """
    Verify that retrieved_context is forwarded to the LLM prompt.
    Proves state.get("retrieved_context") is executed.
    """
    captured_prompts: list = []

    async def capturing_complete(prompt, **kwargs):
        captured_prompts.append(prompt)
        return LLMResponse(
            content="[]",
            prompt_tokens=50,
            completion_tokens=10,
            total_tokens=60,
            model_name="test-model",
        )

    mock_llm = MagicMock(spec=ILLMProvider)
    mock_llm.complete = capturing_complete

    agent = CodeReviewAgent(mock_llm)

    unique_context = "UNIQUE_CONTEXT_SNIPPET_abc123"
    state = {
        "query": "review this code",
        "retrieved_context": unique_context,
        "review_config": {},
        "pending_tasks": ["code_review"],
        "completed_tasks": [],
    }

    await agent.execute(state)

    assert unique_context in captured_prompts[0], (
        f"Expected retrieved_context to appear in the LLM prompt but got:\n{captured_prompts[0]}"
    )


@pytest.mark.asyncio
async def test_code_review_agent_strictness_levels():
    """
    Verify all strictness levels from review_config are propagated without errors.
    Covers the Low / Medium / High review configuration options.
    """
    for strictness in ("low", "medium", "high"):
        llm = _make_llm("[]")
        agent = CodeReviewAgent(llm)

        state = {
            "query": f"Review code at {strictness} strictness",
            "retrieved_context": "def foo(): pass",
            "review_config": {"strictness": strictness},
            "pending_tasks": ["code_review"],
            "completed_tasks": [],
        }

        result = await agent.execute(state)
        assert "agent_outputs" in result, f"Failed for strictness={strictness}"

        call_kwargs = llm.complete.call_args
        prompt_arg = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("prompt", "")
        assert strictness.upper() in prompt_arg, (
            f"Strictness '{strictness.upper()}' not found in prompt for level={strictness}"
        )


@pytest.mark.asyncio
async def test_code_review_agent_empty_state_uses_defaults():
    """
    When state has no query / context / review_config, the agent must
    still execute without error, using empty-string defaults.
    """
    llm = _make_llm("[]")
    agent = CodeReviewAgent(llm)

    state = {
        "pending_tasks": ["code_review"],
        "completed_tasks": [],
    }

    result = await agent.execute(state)
    assert "agent_outputs" in result
    assert result["agent_outputs"]["code_review"]["structured_findings"] == []


@pytest.mark.asyncio
async def test_code_review_agent_parses_structured_findings():
    """
    When the LLM returns a valid JSON array of findings, the agent
    must parse them and return them in structured_findings.
    """
    findings_json = """[
        {
            "issue": "Large function",
            "severity": "high",
            "explanation": "process() is 200 lines long",
            "suggested_fix": "Break into smaller functions",
            "confidence_score": 0.9,
            "file_path": "src/processor.py",
            "line_number": 45
        }
    ]"""
    llm = _make_llm(findings_json)
    agent = CodeReviewAgent(llm)

    state = {
        "query": "Review code quality",
        "retrieved_context": "def process(): ...",
        "review_config": {"strictness": "medium"},
        "pending_tasks": ["code_review"],
        "completed_tasks": [],
    }

    result = await agent.execute(state)
    findings = result["agent_outputs"]["code_review"]["structured_findings"]
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"
    assert findings[0]["issue"] == "Large function"
