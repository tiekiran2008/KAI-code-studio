"""
Planner Agent
=============
Analyzes user intent, decomposes the task into subtasks, and assigns
which specialized engineering agents will run.
"""
import json
import time
from typing import Any, Dict, List, Optional
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
        try:
            llm_resp = await self.llm.complete(
                prompt=prompt,
                system=_PLANNER_SYSTEM_PROMPT,
                max_tokens=1024,
                temperature=0.1,
            )
            plan = self._parse_plan(llm_resp.content, query)
        except Exception as exc:
            logger.warning("planner_llm_failed_fallback_to_heuristic: %s", exc)
            plan = self._parse_plan("", query)

        selected = plan.get("selected_agents", ["context", "code_analysis"])

        # If review_config is provided, ensure all enabled review agents are scheduled deterministically
        review_config = state.get("review_config", {})
        if isinstance(review_config, dict) and review_config:
            candidate_set = set(selected)
            
            # Explicit additions based on review_config flags
            code_qual = review_config.get("code_quality", review_config.get("codeQuality", True))
            sec = review_config.get("security", True)
            perf = review_config.get("performance", True)
            arch = review_config.get("architecture", False)

            if code_qual:
                candidate_set.add("code_review")
                candidate_set.add("code_quality")
                candidate_set.add("refactoring_analysis")
            if sec:
                candidate_set.add("security_review")
            if perf:
                candidate_set.add("performance")
            if arch:
                candidate_set.add("code_quality")

            # Explicit removals if toggled off
            if not sec:
                candidate_set.discard("security_review")
            if not perf:
                candidate_set.discard("performance")
            if not (arch or code_qual):
                candidate_set.discard("code_quality")
            if not code_qual:
                candidate_set.discard("code_review")
                candidate_set.discard("refactoring_analysis")

            # Maintain deterministic ordering: context -> review agents -> quality/refactor
            ordered = ["context"]
            for a in ("code_review", "security_review", "performance", "code_quality", "refactoring_analysis", "documentation"):
                if a in candidate_set and a not in ordered:
                    ordered.append(a)
            # Add any other selected agents
            for a in selected:
                if a in candidate_set and a not in ordered:
                    ordered.append(a)

            selected = ordered if len(ordered) > 1 else ["context", "code_review"]
        else:
            # Make sure context agent is included if any analysis/code agent is requested
            if selected and "context" not in selected:
                selected.insert(0, "context")

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
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            if isinstance(data, dict) and "selected_agents" in data and isinstance(data["selected_agents"], list):
                return data
        except Exception:
            pass

        # Fallback heuristic planning
        query_lower = query.lower()
        agents = ["context"]
        if any(kw in query_lower for kw in ("bug", "error", "fix", "issue", "crash", "exception")):
            agents.append("bug_detection")
        if any(kw in query_lower for kw in ("security", "vulnerability", "auth", "owasp", "leak", "secret")):
            agents.append("security_review")
        if any(kw in query_lower for kw in ("slow", "performance", "optimize", "speed", "latency", "memory", "cpu")):
            agents.append("performance")
        if any(kw in query_lower for kw in ("test", "unit test", "mock", "coverage", "pytest")):
            agents.append("test_generation")
        if any(kw in query_lower for kw in ("document", "docs", "readme", "docstring")):
            agents.append("documentation")
        if any(kw in query_lower for kw in ("review", "solid", "readability")):
            agents.append("code_review")
        if any(kw in query_lower for kw in ("refactor", "smell", "clean code", "debt")):
            agents.append("refactoring_analysis")
        if any(kw in query_lower for kw in ("architecture", "quality", "layer", "health", "coupling")):
            agents.append("code_quality")
        if any(kw in query_lower for kw in ("report", "summary", "export", "pdf", "sarif", "executive", "audit", "full review")):
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
