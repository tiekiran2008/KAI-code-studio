"""
Refactoring Analysis Agent
===========================
Enterprise-grade AI agent that analyzes code review, security, and performance
findings to generate intelligent refactoring recommendations.

IMPORTANT: This agent NEVER modifies source code automatically.
           It ONLY generates recommendations.
"""
import json
import time
from typing import Dict, Any, List
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Principal AI Refactoring Engineer and Staff Software Architect.
Analyze the provided code context alongside existing code-review, security, and performance findings
to generate enterprise-grade refactoring recommendations.

Detect and recommend improvements for:
- Long Methods
- Large Classes
- God Objects
- Duplicate Code
- Dead Code
- Feature Envy
- Data Classes
- Switch Statement Smells
- Deep Nesting
- High Cyclomatic Complexity
- High Cognitive Complexity
- Long Parameter Lists
- Primitive Obsession
- Tight Coupling
- Low Cohesion
- SOLID Principle Violations
- Missing Design Patterns
- Poor Exception Handling
- Poor Naming
- Async Opportunities
- Resource Management Issues

You MUST output ONLY a raw JSON object with this exact structure:
{
  "findings": [
    {
      "refactoring_type": "Extract Method",
      "priority": "high",
      "category": "complexity",
      "file_path": "path/to/file.py",
      "line_number": 42,
      "explanation": "Detailed explanation of why this refactoring is needed",
      "current_problem": "Function process_data exceeds 60 lines with high nesting",
      "suggested_refactoring": "Extract validation logic into validate_input() helper function",
      "before_preview": "Brief text showing the problematic code pattern",
      "after_preview": "Brief text showing the suggested refactored pattern",
      "benefits": ["Improved readability", "Reduced complexity"],
      "risks": ["Requires updating callers"],
      "estimated_effort_hours": 2.0,
      "confidence_score": 0.92
    }
  ],
  "overall_priority": "high",
  "estimated_total_effort_hours": 16.5,
  "estimated_maintainability_improvement": 25.0,
  "estimated_technical_debt_reduction": 12.0,
  "estimated_complexity_reduction": 35.0,
  "summary": "Brief overall summary"
}

Categories must be one of: complexity, duplication, naming, coupling, cohesion, solid, patterns,
                             dead_code, structure, error_handling, async, god_object, feature_envy, smells.
Priority must be one of: critical, high, medium, low.
estimated_maintainability_improvement, estimated_technical_debt_reduction, and estimated_complexity_reduction are percentages (0-100) or hours.
Do NOT wrap the JSON in markdown. Output the raw JSON object starting with { and ending with }.
If no refactoring opportunities are found, return an empty findings array.
"""


class RefactoringAnalysisAgent:
    """Generates refactoring recommendations from accumulated review context.

    Consumes the outputs of the Code Review, Security Review, and Performance
    agents (when available) and produces a structured set of refactoring
    suggestions.  It NEVER modifies source code automatically.
    """

    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm = llm_provider

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        query = state.get("query", "")
        context = state.get("retrieved_context", "No context retrieved.")
        agent_outputs = state.get("agent_outputs", {})

        # Collect prior agent findings to feed into the refactoring prompt.
        prior_findings: List[str] = []
        for agent_key in ("code_review", "security_review", "performance"):
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
            "Analyze the following code context and prior review findings.\n"
            "Generate enterprise-grade refactoring recommendations.\n"
            "Do NOT modify any code automatically – only suggest improvements.\n\n"
            f"Codebase Context:\n{context}\n\n"
            f"Prior Review Findings:\n{prior_context}\n\n"
            "Remember: OUTPUT ONLY RAW JSON."
        )

        llm_resp = await self.llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            max_tokens=4000,
            temperature=0.15,
        )

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("refactoring_analysis_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.REFACTORING_ANALYSIS.value]
        completed = state.get("completed_tasks", []) + [AgentType.REFACTORING_ANALYSIS.value]

        # Parse structured JSON from LLM response
        result: Dict[str, Any] = {}
        findings: List[Dict[str, Any]] = []
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
        except Exception as e:
            logger.error("refactoring_json_parse_error", error=str(e), content=llm_resp.content)
            result = {}
            findings = []

        output = {
            "summary": result.get("summary", f"Completed refactoring analysis, found {len(findings)} suggestions."),
            "details": llm_resp.content,
            "structured_findings": findings,
            "overall_priority": result.get("overall_priority", "medium"),
            "estimated_total_effort_hours": result.get("estimated_total_effort_hours", 0.0),
            "estimated_maintainability_improvement": result.get("estimated_maintainability_improvement", 0.0),
            "estimated_technical_debt_reduction": result.get("estimated_technical_debt_reduction", 0.0),
            "estimated_complexity_reduction": result.get("estimated_complexity_reduction", 0.0),
        }

        return {
            "agent_outputs": {AgentType.REFACTORING_ANALYSIS.value: output},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.REFACTORING_ANALYSIS.value,
            "execution_trace": [{
                "agent": AgentType.REFACTORING_ANALYSIS.value,
                "action": "analyzed_refactoring_opportunities",
                "findings_count": len(findings),
                "latency_ms": latency,
            }],
        }
