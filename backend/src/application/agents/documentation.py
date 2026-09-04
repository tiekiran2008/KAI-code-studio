"""
Documentation Agent
===================
Generates API documentation, docstrings, README sections, and developer guides.
"""
import time
from typing import Dict, Any
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Principal Technical Writer & Developer Advocate.
Generate clear, comprehensive technical documentation for the code context:
- Module & Class docstrings (Google / Sphinx format).
- API endpoint parameters, request/response schemas, and example calls.
- Architectural README setup and usage sections.

Write clean Markdown with syntax-highlighted code blocks.
"""


class DocumentationAgent:
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
            temperature=0.2,
        )

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("documentation_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.DOCUMENTATION.value]
        completed = state.get("completed_tasks", []) + [AgentType.DOCUMENTATION.value]

        output = {
            "summary": "Generated technical documentation and API reference.",
            "details": llm_resp.content,
        }

        return {
            "agent_outputs": {AgentType.DOCUMENTATION.value: output},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.DOCUMENTATION.value,
            "execution_trace": [{
                "agent": AgentType.DOCUMENTATION.value,
                "action": "generated_documentation",
                "latency_ms": latency,
            }],
        }
