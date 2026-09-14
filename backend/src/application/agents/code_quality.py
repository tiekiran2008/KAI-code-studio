"""
AI Architecture & Code Quality Agent
===================================
Enterprise-grade AI agent that evaluates repository health, maintainability, Clean Architecture
compliance, layer dependency violations, module coupling/cohesion, SOLID violations,
design pattern opportunities, documentation coverage, and long-term technical debt.

IMPORTANT: This agent NEVER modifies source code automatically.
           It ONLY analyzes and generates actionable recommendations.
"""
import json
import time
from typing import Dict, Any, List
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Principal Software Architect, Senior Static Analysis Engineer, and Enterprise Code Quality Engineer.
Analyze the codebase structure, context, and prior agent findings (code review, security, performance, refactoring) to evaluate overall repository architecture, maintainability, and code quality.

Analyze:
1. Architecture: Clean Architecture compliance, layer dependency violations (e.g. domain importing infrastructure), circular dependencies, module coupling, cohesion, package/repo organization, microservice boundaries.
2. Maintainability: Maintainability Index, Technical Debt, Code Duplication, Complexity Hotspots, Long Files/Classes/Methods, Dead Code, Unused Imports/Variables, Documentation Coverage.
3. Design: SOLID principle violations, Design pattern opportunities, Repository Pattern compliance, Dependency Injection quality, Separation of Concerns, Encapsulation, Modularity.

You MUST output ONLY a raw JSON object with this exact structure:
{
  "findings": [
    {
      "category": "clean_architecture",
      "severity": "high",
      "priority": "high",
      "file_path": "src/domain/entities/user.py",
      "line_number": 15,
      "explanation": "Domain layer directly imports SQLAlchemy ORM infrastructure model.",
      "root_cause": "Tightly coupled domain model with database persistence layer.",
      "business_impact": "Prevents switching database drivers or testing domain logic in isolation.",
      "recommendation": "Decouple domain entity from ORM model using mapping interface or DTO.",
      "estimated_effort_hours": 3.5,
      "confidence_score": 0.95
    }
  ],
  "metrics": {
    "overall_health_score": 82.5,
    "architecture_score": 85.0,
    "maintainability_score": 78.0,
    "technical_debt_score": 75.0,
    "complexity_score": 80.0,
    "documentation_score": 88.0,
    "modularity_score": 84.0,
    "testability_score": 86.0
  },
  "dependency_analysis": {
    "layer_violations": [
      {
        "source_layer": "domain",
        "target_layer": "infrastructure",
        "source_file": "src/domain/services/user_service.py",
        "target_file": "src/infrastructure/db.py",
        "description": "Domain service imports infrastructure DB helper."
      }
    ],
    "circular_dependencies": [],
    "hotspot_files": [
      {
        "file_path": "src/application/use_cases/review_code.py",
        "complexity_score": 85.0,
        "technical_debt_hours": 12.0,
        "issue_count": 4
      }
    ]
  },
  "summary": "Repository displays solid Clean Architecture patterns with minor layer coupling issues."
}

Categories must be one of: architecture, clean_architecture, coupling, cohesion, solid, patterns, technical_debt, complexity, documentation, testability, layer_violation, modularity.
Severity and Priority must be one of: critical, high, medium, low, info.
Metrics scores are floats from 0.0 to 100.0 (where 100 is best).
Do NOT wrap the JSON in markdown. Output the raw JSON object starting with { and ending with }.
If no quality issues are found, return an empty findings array and default 100.0 metric scores.
"""


class CodeQualityAgent:
    """Evaluates architecture quality, Clean Architecture compliance, maintainability, and health metrics.

    Consumes context and outputs from Code Review, Security, Performance, and Refactoring agents.
    NEVER modifies source code automatically.
    """

    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm = llm_provider

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        query = state.get("query", "")
        context = state.get("retrieved_context", "No context retrieved.")
        agent_outputs = state.get("agent_outputs", {})

        # Collect prior findings across code review, security, performance, and refactoring
        prior_findings: List[str] = []
        for agent_key in ("code_review", "security_review", "performance", "refactoring_analysis"):
            output = agent_outputs.get(agent_key)
            if output:
                findings = output.get("structured_findings", [])
                if findings:
                    prior_findings.append(
                        f"--- {agent_key.upper()} FINDINGS ---\n{json.dumps(findings, indent=2)}"
                    )

        prior_context = "\n\n".join(prior_findings) if prior_findings else "No prior findings available."

        prompt = (
            f"User Request: {query}\n\n"
            "Analyze the codebase architecture, module organization, Clean Architecture compliance, and prior findings.\n"
            "Generate repository-wide metrics, architecture findings, and layer dependency analysis.\n"
            "Do NOT modify any code automatically – only analyze and recommend.\n\n"
            f"Codebase Context:\n{context}\n\n"
            f"Prior Review Agent Outputs:\n{prior_context}\n\n"
            "Remember: OUTPUT ONLY RAW JSON."
        )

        llm_resp = await self.llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            max_tokens=4000,
            temperature=0.15,
        )

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("code_quality_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.CODE_QUALITY.value]
        completed = state.get("completed_tasks", []) + [AgentType.CODE_QUALITY.value]

        # Parse JSON
        result: Dict[str, Any] = {}
        findings: List[Dict[str, Any]] = []
        metrics: Dict[str, float] = {}
        dependency_analysis: Dict[str, Any] = {}

        try:
            content = llm_resp.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            result = json.loads(content.strip())
            findings = result.get("findings", [])
            metrics = result.get("metrics", {})
            dependency_analysis = result.get("dependency_analysis", {})
            if not metrics and not findings and result:
                metrics = {
                    "overall_health_score": 100.0,
                    "architecture_score": 100.0,
                    "maintainability_score": 100.0,
                    "technical_debt_score": 100.0,
                    "complexity_score": 100.0,
                    "documentation_score": 100.0,
                    "modularity_score": 100.0,
                    "testability_score": 100.0,
                }
        except Exception as e:
            logger.error("code_quality_json_parse_error", error=str(e), content=llm_resp.content)
            result = {}

        output = {
            "summary": result.get("summary", f"Completed architecture & code quality analysis, found {len(findings)} issues."),
            "details": llm_resp.content,
            "structured_findings": findings,
            "metrics": metrics,
            "dependency_analysis": dependency_analysis,
        }

        return {
            "agent_outputs": {AgentType.CODE_QUALITY.value: output},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.CODE_QUALITY.value,
            "execution_trace": [{
                "agent": AgentType.CODE_QUALITY.value,
                "action": "analyzed_architecture_and_quality",
                "findings_count": len(findings),
                "latency_ms": latency,
            }],
        }
