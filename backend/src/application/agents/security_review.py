"""
Security Review Agent
=====================
Audits codebase context against OWASP top vulnerabilities, hardcoded secrets,
SQL injection, XSS, and authentication/authorization issues.
"""
import json
import time
from typing import Dict, Any, List
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Senior Application Security Engineer & Vulnerability Researcher.
Perform a security audit strictly grounded in the provided code context.

STRICT GROUNDING & CITATION RULES:
1. Every reported security risk must be directly observable in the retrieved code chunks. Never invent vulnerabilities, files, or line numbers.
2. The `file_path` and `line_number` MUST exist in and match the provided context lines.
3. If no security vulnerabilities are found, return an empty array `[]`.
4. Severity must be one of: critical, high, medium, low, info.

You MUST output ONLY a raw JSON array of finding objects adhering to this schema:
[
  {
    "vulnerability": "SQL Injection in User Search",
    "issue": "SQL Injection in User Search",
    "severity": "critical",
    "cwe_id": "CWE-89",
    "owasp_category": "A03:2021-Injection",
    "file_path": "src/api/users.py",
    "line_number": 42,
    "explanation": "Raw user input concatenated directly into SQL query string.",
    "attack_scenario": "Attacker supplies ' OR 1=1 -- to dump database tables.",
    "suggested_fix": "Use parameterized queries with SQLAlchemy text bind parameters.",
    "confidence_score": 0.95
  }
]
Do not wrap the JSON in Markdown code blocks. Output the raw JSON array starting with `[` and ending with `]`.
If no security vulnerabilities are found, return an empty array `[]`.
"""


class SecurityReviewAgent:
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
        logger.info("security_review_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.SECURITY_REVIEW.value]
        completed = state.get("completed_tasks", []) + [AgentType.SECURITY_REVIEW.value]

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
            logger.error("security_review_json_parse_error", error=str(e), content=llm_resp.content)
            findings = []

        output = {
            "summary": f"Completed security review, found {len(findings)} security vulnerabilities.",
            "details": llm_resp.content,
            "structured_findings": findings,
        }

        return {
            "agent_outputs": {AgentType.SECURITY_REVIEW.value: output},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.SECURITY_REVIEW.value,
            "execution_trace": [{
                "agent": AgentType.SECURITY_REVIEW.value,
                "action": "audited_security_vulnerabilities",
                "findings_count": len(findings),
                "latency_ms": latency,
            }],
        }
