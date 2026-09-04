"""
Test Generation Agent
=====================
Generates unit tests, integration tests, mock objects, and edge cases.
"""
import time
from typing import Dict, Any
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Lead Software Test Automation Engineer.
Generate production-ready test suites for the provided code context:
- Unit tests using standard frameworks (e.g., pytest, unittest, JUnit).
- Edge-case testing (null inputs, boundary limits, exception paths).
- Mock objects and dependency stubs (e.g., unittest.mock, MagicMock).

Provide idiomatic, ready-to-run test code.
"""


class TestGenerationAgent:
    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm = llm_provider

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        query = state.get("query", "")
        context = state.get("retrieved_context", "No context retrieved.")

        prompt = f"User Request: {query}\n\nCodebase Context:\n{context}"

        llm_resp = await self.llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            max_tokens=1800,
            temperature=0.1,
        )

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("test_generation_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.TEST_GENERATION.value]
        completed = state.get("completed_tasks", []) + [AgentType.TEST_GENERATION.value]

        output = {
            "summary": "Generated comprehensive unit tests and mock objects.",
            "details": llm_resp.content,
        }

        return {
            "agent_outputs": {AgentType.TEST_GENERATION.value: output},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.TEST_GENERATION.value,
            "execution_trace": [{
                "agent": AgentType.TEST_GENERATION.value,
                "action": "generated_unit_tests",
                "latency_ms": latency,
            }],
        }
