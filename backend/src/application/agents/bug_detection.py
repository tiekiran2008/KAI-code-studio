"""
Bug Detection Agent
===================
Identifies logic errors, runtime exception risks, null pointer risks,
and resource leaks in the codebase context.
"""
import time
from typing import Dict, Any
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Principal Software Quality Engineer & Bug Auditor.
Scan the provided code context for potential defects:
- Null pointer / AttributeError dereferencing risks
- Resource leaks (unclosed files, DB connections, sockets)
- Edge-case logic bugs, uncaught exceptions, off-by-one errors
- Unhandled async/thread synchronization hazards

Provide concrete root cause explanations and suggested fixes with code snippets.
"""


class BugDetectionAgent:
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
            max_tokens=1500,
            temperature=0.1,
        )

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("bug_detection_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.BUG_DETECTION.value]
        completed = state.get("completed_tasks", []) + [AgentType.BUG_DETECTION.value]

        output = {
            "summary": "Completed bug detection audit and root-cause analysis.",
            "details": llm_resp.content,
        }

        return {
            "agent_outputs": {AgentType.BUG_DETECTION.value: output},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.BUG_DETECTION.value,
            "execution_trace": [{
                "agent": AgentType.BUG_DETECTION.value,
                "action": "audited_code_bugs",
                "latency_ms": latency,
            }],
        }
