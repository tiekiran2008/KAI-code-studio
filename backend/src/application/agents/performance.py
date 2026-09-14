"""
Performance Agent
=================
Analyzes algorithmic complexity (Big-O), memory allocation efficiency,
expensive loops, N+1 query patterns, and performance bottlenecks.
"""
import json
import time
from typing import Dict, Any, List
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Principal Performance Optimization & Distributed Systems Engineer.
Analyze the performance characteristics of the codebase context strictly based on code evidence.

STRICT GROUNDING RULES:
1. Every performance bottleneck must be directly observable in the retrieved code chunks. Never invent issues, files, or line numbers.
2. The `file_path` and `line_number` MUST exist in and match the provided context lines.
3. If no performance issues are found, return an empty array `[]`.
4. Severity must be one of: critical, high, medium, low, info.

You MUST output ONLY a raw JSON array of finding objects adhering to this schema:
[
  {
    "issue": "N+1 Query Pattern in Loop",
    "severity": "high",
    "estimated_impact": "High database query volume causing latency spike under traffic",
    "file_path": "src/services/order_service.py",
    "line_number": 55,
    "root_cause": "Individual SQL query executed for each item inside iteration instead of batch query",
    "suggested_optimization": "Use joinedload / selectinload or batch IN clause to query all items in one trip",
    "expected_performance_gain": "80%",
    "confidence_score": 0.92
  }
]
Do not wrap the JSON in Markdown code blocks. Output the raw JSON array starting with `[` and ending with `]`.
If no performance issues are found, return an empty array `[]`.
"""


class PerformanceAgent:
    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm = llm_provider

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        query = state.get("query", "")
        context = state.get("retrieved_context", "No context retrieved.")
        review_config = state.get("review_config", {})
        strictness = review_config.get("strictness", "medium")

        prompt = (
            f"User Request: {query}\n"
            f"Review Strictness Level: {strictness.upper()}\n\n"
            f"Codebase Context:\n{context}\n\n"
            "Remember: OUTPUT ONLY RAW JSON ARRAY."
        )

        llm_resp = await self.llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            max_tokens=3000,
            temperature=0.1,
        )

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("performance_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.PERFORMANCE.value]
        completed = state.get("completed_tasks", []) + [AgentType.PERFORMANCE.value]

        findings: List[Dict[str, Any]] = []
        try:
            content = llm_resp.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            data = json.loads(content.strip())
            if isinstance(data, list):
                findings = data
            elif isinstance(data, dict) and "findings" in data and isinstance(data["findings"], list):
                findings = data["findings"]
        except Exception as e:
            logger.error("performance_json_parse_error", error=str(e), content=llm_resp.content)
            findings = []

        output = {
            "summary": f"Completed performance analysis, found {len(findings)} issues.",
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
                "findings_count": len(findings),
                "latency_ms": latency,
            }],
        }
