"""
Security Review Agent
=====================
Audits codebase context against OWASP top vulnerabilities, hardcoded secrets,
SQL injection, XSS, and authentication/authorization issues.
"""
import time
from typing import Dict, Any
from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.core.logger import logger

_SYSTEM_PROMPT = """You are a Senior Application Security Engineer & Vulnerability Researcher.
Perform a security audit of the provided code context:
- OWASP Top 10 risks (SQL Injection, XSS, CSRF, SSRF)
- Hardcoded secrets, API keys, credentials, or insecure defaults
- Broken authentication, weak token validation, missing authorization guards
- Dangerous input deserialization or command execution

Classify severity (Critical, High, Medium, Low) and provide remediations.
"""


class SecurityReviewAgent:
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
        logger.info("security_review_agent_complete", latency_ms=latency)

        pending = [t for t in state.get("pending_tasks", []) if t != AgentType.SECURITY_REVIEW.value]
        completed = state.get("completed_tasks", []) + [AgentType.SECURITY_REVIEW.value]

        output = {
            "summary": "Completed security review and vulnerability assessment.",
            "details": llm_resp.content,
        }

        return {
            "agent_outputs": {AgentType.SECURITY_REVIEW.value: output},
            "pending_tasks": pending,
            "completed_tasks": completed,
            "sender": AgentType.SECURITY_REVIEW.value,
            "execution_trace": [{
                "agent": AgentType.SECURITY_REVIEW.value,
                "action": "audited_security_vulnerabilities",
                "latency_ms": latency,
            }],
        }
