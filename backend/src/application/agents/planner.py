"""
Planner Agent
=============
Analyzes user intent, decomposes the task into subtasks, and assigns
which specialized engineering agents will run.
"""
import json
import time
from typing import Dict, Any, List
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_PLANNER_SYSTEM_PROMPT = """You are a Lead Technical Program Manager and Software Architect.
Analyze the user's software query and select the required specialized engineering agents.

Available Agents:
- context: Retrieve repository code snippets and facts via RAG. (REQUIRED FIRST IF CODE NEEDED)
- code_analysis: Explain functions, classes, architecture, design patterns, dependencies.
- bug_detection: Identify logic errors, null pointer risks, resource leaks, runtime bugs.
- security_review: Security vulnerabilities, OWASP checks, hardcoded secrets, SQLi, XSS.
- performance: Inefficient loops, memory usage, algorithm complexity (Big-O), bottlenecks.
- documentation: API documentation, README sections, architecture guides.
- test_generation: Write unit tests, integration tests, edge cases, mocks.
- code_review: Professional code review, SOLID principles, readability, refactoring.
- refactoring_analysis: Intelligent code refactoring recommendations, design pattern improvements, code smell detection.
- code_quality: Architecture analysis, Clean Architecture compliance, layer dependency violations, maintainability index, repository health metrics.
- report_generation: Aggregate all agent outputs into a comprehensive engineering report (executive summary, risk assessment, health metrics, priority action plan). Use after code_review, security_review, performance, refactoring_analysis, and code_quality.

Return ONLY a JSON object in this exact format:
{
  "summary": "Short explanation of the execution strategy",
  "selected_agents": ["context", "code_analysis", "bug_detection"],
  "parallel_groups": [
    ["context"],
    ["code_analysis", "bug_detection"]
  ]
}
"""


class PlannerAgent:
    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm = llm_provider

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        query = state.get("query", "")

        logger.info("planner_execution_start", query=query[:60])

        prompt = f"User Request: {query}\nDecompose this task and return JSON plan."

        llm_resp = await self.llm.complete(
            prompt=prompt,
            system=_PLANNER_SYSTEM_PROMPT,
            max_tokens=1024,
            temperature=0.1,
        )

        plan = self._parse_plan(llm_resp.content, query)
        selected = plan.get("selected_agents", ["context", "code_analysis"])

        # Make sure context agent is included if any analysis/code agent is requested
        if selected and "context" not in selected:
            selected.insert(0, "context")

        # Respect user review_config check toggles if passed
        review_config = state.get("review_config", {})
        if isinstance(review_config, dict) and review_config:
            filtered = []
            for agent_name in selected:
                if agent_name == "security_review" and not review_config.get("security", True):
                    continue
                if agent_name == "performance" and not review_config.get("performance", True):
                    continue
                if agent_name == "code_quality" and not (review_config.get("architecture", False) or review_config.get("code_quality", True) or review_config.get("codeQuality", True)):
                    continue
                filtered.append(agent_name)
            selected = filtered if filtered else ["context", "code_review"]

        plan["selected_agents"] = selected

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("planner_execution_complete", selected_agents=selected, latency_ms=latency)

        # Route first to context agent if selected, else to first agent in list
        next_agent = selected[0] if selected else AgentType.CODE_ANALYSIS.value

        return {
            "plan": plan,
            "pending_tasks": selected.copy(),
            "completed_tasks": [],
            "next_agent": next_agent,
            "sender": AgentType.PLANNER.value,
            "execution_trace": [{
                "agent": AgentType.PLANNER.value,
                "action": "plan_created",
                "selected_agents": selected,
                "latency_ms": latency,
            }],
        }

    def _parse_plan(self, content: str, query: str) -> Dict[str, Any]:
        """Safely parse LLM output into a plan dict."""
        try:
            # Strip markdown fence if present
            cleaned = content.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            return json.loads(cleaned)
        except Exception:
            # Fallback heuristic planning
            query_lower = query.lower()
            agents = ["context"]
            if "bug" in query_lower or "error" in query_lower or "fix" in query_lower:
                agents.append("bug_detection")
            if "security" in query_lower or "vulnerability" in query_lower or "auth" in query_lower:
                agents.append("security_review")
            if "slow" in query_lower or "performance" in query_lower or "optimize" in query_lower:
                agents.append("performance")
            if "test" in query_lower or "mock" in query_lower:
                agents.append("test_generation")
            if "doc" in query_lower or "readme" in query_lower:
                agents.append("documentation")
            if "review" in query_lower or "solid" in query_lower:
                agents.append("code_review")
            if "refactor" in query_lower or "smell" in query_lower or "clean code" in query_lower or "debt" in query_lower:
                agents.append("refactoring_analysis")
            if "architecture" in query_lower or "quality" in query_lower or "layer" in query_lower or "health" in query_lower or "coupling" in query_lower:
                agents.append("code_quality")
            if "report" in query_lower or "summary" in query_lower or "export" in query_lower or "pdf" in query_lower or "sarif" in query_lower or "executive" in query_lower:
                # Ensure all upstream analysis agents are included
                for a in ("code_review", "security_review", "performance", "refactoring_analysis", "code_quality"):
                    if a not in agents:
                        agents.append(a)
                agents.append("report_generation")
            if len(agents) == 1:
                agents.append("code_analysis")

            return {
                "summary": "Heuristic fallback plan based on query keywords",
                "selected_agents": agents,
                "parallel_groups": [["context"], agents[1:]],
            }
