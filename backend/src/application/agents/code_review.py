"""
Code Review Agent
=================
Evaluates readability, maintainability, SOLID principles, naming conventions,
and refactoring opportunities, producing a structured JSON report.
"""
import time
import json
from typing import Dict, Any
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Principal AI Code Reviewer.
Conduct a rigorous code review on the provided code context.

Focus on detecting:
- Large functions
- Duplicate code
- Poor naming
- Long parameter lists
- Dead code
- Missing documentation
- Complex logic
- Deep nesting
- SOLID violations
- Design pattern misuse
- High cyclomatic complexity

You MUST output ONLY a raw JSON array of finding objects, strictly adhering to this schema:
[
  {
    "issue": "Brief title of the issue",
    "severity": "critical" | "high" | "medium" | "low" | "info",
    "explanation": "Detailed explanation of why this is an issue",
    "suggested_fix": "Code snippet or instruction for fixing it",
    "confidence_score": 0.95,
    "file_path": "path/to/file.py",
    "line_number": 42
  }
]
Do not wrap the JSON in Markdown code blocks. Output the raw JSON array starting with `[` and ending with `]`.
If no issues are found, return an empty array `[]`.
"""

class CodeReviewAgent:
    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm = llm_provider

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        review_config = state.get("review_config", {})
        strictness = review_config.get("strictness", "medium")

        prompt = f"User Request: {query}\nReview Strictness Level: {strictness.upper()}\n\nCodebase Context:\n{context}\n\nRemember: OUTPUT ONLY RAW JSON."

        llm_resp = await self.llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            max_tokens=4000,
            temperature=0.1,
        )

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("code_review_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.CODE_REVIEW.value]
        completed = state.get("completed_tasks", []) + [AgentType.CODE_REVIEW.value]

        # Attempt to parse JSON
        findings = []
        try:
            content = llm_resp.content.strip()
            # Handle potential markdown wrapping
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            findings = json.loads(content.strip())
        except Exception as e:
            logger.error("code_review_json_parse_error", error=str(e), content=llm_resp.content)
            # Fallback or empty if parsing fails
            findings = []

        output = {
            "summary": f"Completed code review, found {len(findings)} issues.",
            "details": "Structured JSON findings generated.",
            "structured_findings": findings
        }

        return {
            "agent_outputs": {AgentType.CODE_REVIEW.value: output},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.CODE_REVIEW.value,
            "execution_trace": [{
                "agent": AgentType.CODE_REVIEW.value,
                "action": "reviewed_code_quality",
                "findings_count": len(findings),
                "latency_ms": latency,
            }],
        }
