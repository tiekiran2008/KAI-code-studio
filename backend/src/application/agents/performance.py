"""
Performance Agent
=================
Analyzes algorithmic complexity (Big-O), memory allocation efficiency,
expensive loops, N+1 query patterns, and performance bottlenecks.
"""
import json
import time
from typing import Dict, Any
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Performance Optimization & Distributed Systems Specialist.
Analyze the performance characteristics of the code context:
- Estimate Time and Space complexity (Big-O notation).
- Identify nested loops, N+1 queries, unindexed queries, or blocking IO operations.
- Highlight excessive memory allocations or missing caching opportunities.
- Recommend concrete algorithmic optimizations.
"""


class PerformanceAgent:
    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm = llm_provider

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        query = state.get("query", "")
        context = state.get("retrieved_context", "No context retrieved.")

        # Build a detailed prompt for performance analysis, instructing the LLM to output structured JSON findings.
        prompt = (
            f"User Request: {query}\n\n"
            "You are an expert performance engineer. Analyze the provided code context for performance issues.\n"
            "Detect N+1 queries, missing indexes, inefficient SQL, blocking I/O, async misuse, memory leaks, large object allocations, inefficient algorithms, missing caching, etc.\n"
            "Return ONLY a raw JSON array of finding objects with the following fields: issue, severity, estimated_impact, file_path, line_number, root_cause, suggested_optimization, expected_performance_gain, confidence_score.\n"
            "Do not wrap the JSON in markdown. Output the raw JSON array."
            f"\n\nCodebase Context:\n{context}"
        )

        llm_resp = await self.llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            max_tokens=1500,
            temperature=0.1,
        )

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("performance_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.PERFORMANCE.value]
        completed = state.get("completed_tasks", []) + [AgentType.PERFORMANCE.value]

        # Parse JSON findings from LLM response
        findings = []
        try:
            content = llm_resp.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            findings = json.loads(content)
        except Exception as e:
            logger.error("performance_json_parse_error", error=str(e), content=llm_resp.content)
            findings = []

        output = {
            "summary": "Completed performance analysis and complexity estimation.",
            "details": llm_resp.content,
            "structured_findings": findings,
        }

        return {
            "agent_outputs": {AgentType.PERFORMANCE.value: output},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.PERFORMANCE.value,
            "execution_trace": [{
                "agent": AgentType.PERFORMANCE.value,
                "action": "analyzed_performance_complexity",
                "latency_ms": latency,
            }],
        }
