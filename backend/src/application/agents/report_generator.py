"""
AI Report Generator Agent
==========================
LangGraph node that aggregates outputs from ALL prior analysis agents
(Code Review, Security, Performance, Refactoring, Code Quality) and
generates a structured EngineeringReportData payload covering 15 report
sections.

IMPORTANT: This agent NEVER modifies source code.
           It ONLY synthesises existing agent outputs into a structured report.
"""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.domain.interfaces.llm import ILLMProvider
from src.domain.models.agents import AgentState, AgentType
from src.domain.entities.report_entity import (
    EngineeringReportData,
    EngineeringReportMetrics,
    ActionItem,
)
from src.core.logger import logger

# ── System prompt ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a Principal Engineering Intelligence Engine and a Technical Report Writer.

Your task is to synthesise the outputs from five specialized engineering analysis agents into a
single, executive-quality engineering report. You receive:
- Code Review findings
- Security findings
- Performance findings
- Refactoring recommendations
- Architecture & Code Quality findings and metrics

You MUST output ONLY a raw JSON object with this exact structure (no markdown fences):
{
  "executive_summary": "Three-paragraph narrative covering overall health, top 3 risks, and recommended next steps.",
  "repository_overview": {
    "primary_languages": ["Python", "TypeScript"],
    "primary_framework": "FastAPI + React",
    "tech_stack_summary": "...",
    "architecture_style": "Clean Architecture / Microservice",
    "overall_maturity": "mature | growing | early"
  },
  "code_review_summary": "Concise paragraph summarising code review findings.",
  "security_summary": "Concise paragraph summarising security findings and severity distribution.",
  "performance_summary": "Concise paragraph summarising performance bottlenecks and potential gains.",
  "refactoring_summary": "Concise paragraph summarising refactoring debt and key recommendations.",
  "architecture_summary": "Concise paragraph summarising architecture issues and health scores.",
  "tech_debt_summary": "Estimated hours and breakdown by category.",
  "total_technical_debt_hours": 42.5,
  "tech_debt_breakdown": {
    "code_review": 8.0,
    "security": 5.0,
    "performance": 7.0,
    "refactoring": 12.0,
    "architecture": 10.5
  },
  "complexity_summary": "Paragraph about complexity hotspots.",
  "maintainability_summary": "Paragraph about maintainability index and long-term risks.",
  "risk_level": "high",
  "risk_summary": "Concise risk narrative.",
  "risk_factors": [
    "3 critical security vulnerabilities (OWASP Top 10)",
    "High coupling between domain and infrastructure layers"
  ],
  "future_improvements": [
    "Adopt hexagonal architecture for domain isolation",
    "Implement automated security scanning in CI pipeline"
  ],
  "future_improvements_summary": "Paragraph about recommended long-term improvements."
}

Rules:
- risk_level must be one of: critical | high | medium | low
- total_technical_debt_hours is a float (estimated from all findings)
- future_improvements is a list of 3-7 concise action strings
- risk_factors is a list of 2-5 concise factor strings
- Do NOT wrap the JSON in markdown. Output raw JSON starting with { and ending with }.
- Write summaries in professional engineering English. Be specific, not generic.
- tech_debt_breakdown keys: code_review, security, performance, refactoring, architecture
"""


class ReportGeneratorAgent:
    """
    Aggregates all prior agent outputs into a structured EngineeringReportData payload.

    This agent:
    1. Collects findings from code_review, security_review, performance,
       refactoring_analysis, and code_quality agents.
    2. Calls the LLM to generate narrative summaries and risk assessment.
    3. Builds an EngineeringReportData with all 15 report sections.
    4. Returns the full payload in agent_outputs under the key 'report_generation'.
    """

    def __init__(self, llm_provider: ILLMProvider) -> None:
        self.llm = llm_provider

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        start = time.perf_counter()
        query          = state.get("query", "")
        repo_id        = state.get("repo_id", "")
        agent_outputs  = state.get("agent_outputs", {})

        # ── 1. Collect raw findings from all prior agents ──────────────────
        code_review_out    = agent_outputs.get(AgentType.CODE_REVIEW.value, {})
        security_out       = agent_outputs.get(AgentType.SECURITY_REVIEW.value, {})
        performance_out    = agent_outputs.get(AgentType.PERFORMANCE.value, {})
        refactoring_out    = agent_outputs.get(AgentType.REFACTORING_ANALYSIS.value, {})
        code_quality_out   = agent_outputs.get(AgentType.CODE_QUALITY.value, {})

        code_review_findings   = code_review_out.get("structured_findings", [])
        security_findings      = security_out.get("structured_findings", [])
        performance_findings   = performance_out.get("structured_findings", [])
        performance_recs       = performance_out.get("structured_recommendations", [])
        refactoring_findings   = refactoring_out.get("structured_findings", [])
        architecture_findings  = code_quality_out.get("structured_findings", [])
        quality_metrics        = code_quality_out.get("metrics", {})
        dependency_analysis    = code_quality_out.get("dependency_analysis", {})

        # ── 2. Build per-agent summaries for the LLM prompt ───────────────
        def _summarise(name: str, findings: list) -> str:
            if not findings:
                return f"{name}: No findings."
            counts = {}
            for f in findings:
                sev = (f.get("severity") or f.get("priority") or "info").lower()
                counts[sev] = counts.get(sev, 0) + 1
            count_str = ", ".join(f"{v} {k}" for k, v in counts.items())
            return f"{name}: {len(findings)} findings ({count_str})."

        agent_summary = "\n".join([
            _summarise("Code Review",   code_review_findings),
            _summarise("Security",      security_findings),
            _summarise("Performance",   performance_findings),
            _summarise("Refactoring",   refactoring_findings),
            _summarise("Architecture",  architecture_findings),
        ])

        metrics_text = json.dumps(quality_metrics, indent=2) if quality_metrics else "No metrics available."

        # Truncate findings to keep prompt manageable
        def _compact(findings: list, max_items: int = 8) -> str:
            subset = findings[:max_items]
            return json.dumps(subset, indent=2) if subset else "[]"

        prompt = (
            f"Repository ID: {repo_id}\n"
            f"User Query: {query}\n\n"
            f"Agent Output Summary:\n{agent_summary}\n\n"
            f"Architecture Quality Metrics:\n{metrics_text}\n\n"
            f"Code Review Findings (top 8):\n{_compact(code_review_findings)}\n\n"
            f"Security Findings (top 8):\n{_compact(security_findings)}\n\n"
            f"Performance Findings (top 8):\n{_compact(performance_findings)}\n\n"
            f"Refactoring Findings (top 8):\n{_compact(refactoring_findings)}\n\n"
            f"Architecture Findings (top 8):\n{_compact(architecture_findings)}\n\n"
            "Generate the engineering report JSON object. OUTPUT ONLY RAW JSON."
        )

        # ── 3. Call LLM for narrative content ─────────────────────────────
        llm_resp = await self.llm.complete(
            prompt=prompt,
            system=_SYSTEM_PROMPT,
            max_tokens=4000,
            temperature=0.15,
        )

        latency = round((time.perf_counter() - start) * 1000, 2)
        logger.info("report_generator_llm_complete", latency_ms=latency)

        # ── 4. Parse LLM output ────────────────────────────────────────────
        llm_data: Dict[str, Any] = {}
        try:
            content = llm_resp.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            llm_data = json.loads(content.strip())
        except Exception as e:
            logger.error("report_generator_json_parse_error", error=str(e))

        # ── 5. Build aggregated metrics ────────────────────────────────────
        metrics = _build_metrics(
            quality_metrics  = quality_metrics,
            security_findings = security_findings,
            performance_out  = performance_out,
            refactoring_out  = refactoring_out,
            code_review_findings = code_review_findings,
        )

        # ── 6. Build Priority Action Plan from critical/high findings ─────
        action_items = _build_action_plan(
            code_review_findings  = code_review_findings,
            security_findings     = security_findings,
            performance_findings  = performance_findings,
            refactoring_findings  = refactoring_findings,
            architecture_findings = architecture_findings,
        )

        # ── 7. Hotspot files from dependency analysis ──────────────────────
        hotspot_files = dependency_analysis.get("hotspot_files", [])

        # ── 8. Assemble EngineeringReportData ─────────────────────────────
        now  = datetime.now(timezone.utc).isoformat()
        report_id = str(uuid.uuid4())

        report_data = EngineeringReportData(
            report_id            = report_id,
            review_id            = state.get("session_id", ""),
            repository_id        = repo_id,
            repository_name      = llm_data.get("repository_overview", {}).get("primary_framework", repo_id),
            generated_at         = now,
            report_version       = "1.0",
            executive_summary    = llm_data.get("executive_summary", ""),
            repository_overview  = llm_data.get("repository_overview", {}),
            code_review_findings    = code_review_findings,
            code_review_summary     = llm_data.get("code_review_summary", ""),
            security_findings       = security_findings,
            security_summary        = llm_data.get("security_summary", ""),
            performance_findings    = performance_findings,
            performance_recommendations = performance_recs,
            performance_summary     = llm_data.get("performance_summary", ""),
            refactoring_findings    = refactoring_findings,
            refactoring_summary     = llm_data.get("refactoring_summary", ""),
            architecture_findings   = architecture_findings,
            dependency_analysis     = dependency_analysis,
            architecture_summary    = llm_data.get("architecture_summary", ""),
            metrics                 = metrics,
            total_technical_debt_hours = float(llm_data.get("total_technical_debt_hours", 0.0)),
            tech_debt_breakdown     = llm_data.get("tech_debt_breakdown", {}),
            tech_debt_summary       = llm_data.get("tech_debt_summary", ""),
            complexity_hotspots     = [],
            complexity_summary      = llm_data.get("complexity_summary", ""),
            maintainability_issues  = [],
            maintainability_summary = llm_data.get("maintainability_summary", ""),
            hotspot_files           = hotspot_files,
            risk_level              = llm_data.get("risk_level", "medium"),
            risk_factors            = llm_data.get("risk_factors", []),
            risk_summary            = llm_data.get("risk_summary", ""),
            action_items            = action_items,
            future_improvements     = llm_data.get("future_improvements", []),
            future_improvements_summary = llm_data.get("future_improvements_summary", ""),
        )

        # ── 9. Update state ────────────────────────────────────────────────
        from dataclasses import asdict
        pending   = [t for t in state.get("pending_tasks", []) if t != AgentType.REPORT_GENERATION.value]
        completed = state.get("completed_tasks", []) + [AgentType.REPORT_GENERATION.value]

        output = {
            "summary":        f"Engineering report generated with {len(action_items)} priority action items.",
            "details":        llm_resp.content,
            "report_data":    asdict(report_data),
            "metrics":        {
                "overall_health_score":  metrics.overall_health_score,
                "risk_score":            metrics.risk_score,
                "security_score":        metrics.security_score,
                "performance_score":     metrics.performance_score,
                "architecture_score":    metrics.architecture_score,
                "maintainability_score": metrics.maintainability_score,
                "technical_debt_score":  metrics.technical_debt_score,
                "complexity_score":      metrics.complexity_score,
                "documentation_score":   metrics.documentation_score,
                "testability_score":     metrics.testability_score,
            },
            "action_items_count":  len(action_items),
            "total_findings":      (
                len(code_review_findings) + len(security_findings) +
                len(performance_findings) + len(refactoring_findings) +
                len(architecture_findings)
            ),
            "risk_level":  report_data.risk_level,
        }

        logger.info(
            "report_generator_complete",
            latency_ms=latency,
            action_items=len(action_items),
            risk_level=report_data.risk_level,
        )

        return {
            "agent_outputs": {AgentType.REPORT_GENERATION.value: output},
            "pending_tasks":  pending,
            "completed_tasks": completed,
            "sender":          AgentType.REPORT_GENERATION.value,
            "execution_trace": [{
                "agent":          AgentType.REPORT_GENERATION.value,
                "action":         "generated_engineering_report",
                "action_items":   len(action_items),
                "risk_level":     report_data.risk_level,
                "latency_ms":     latency,
            }],
        }


# ── Private helpers ────────────────────────────────────────────────────────────

def _build_metrics(
    quality_metrics:      Dict[str, Any],
    security_findings:    List[Dict],
    performance_out:      Dict[str, Any],
    refactoring_out:      Dict[str, Any],
    code_review_findings: List[Dict],
) -> EngineeringReportMetrics:
    """Aggregate all agent scores into one EngineeringReportMetrics object."""

    # Architecture scores from Code Quality Agent
    overall_health   = quality_metrics.get("overall_health_score", 0.0)
    arch_score       = quality_metrics.get("architecture_score", 0.0)
    maint_score      = quality_metrics.get("maintainability_score", 0.0)
    debt_score       = quality_metrics.get("technical_debt_score", 0.0)
    complexity_score = quality_metrics.get("complexity_score", 80.0)
    doc_score        = quality_metrics.get("documentation_score", 85.0)
    test_score       = quality_metrics.get("testability_score", 84.0)

    # Performance score
    perf_score = performance_out.get("performance_score") or 0.0

    # Security score — derived from finding severities
    sec_score = _findings_to_score(security_findings)

    # Code review score — derived from finding severities
    cr_score  = _findings_to_score(code_review_findings)

    # Overall health — blend if not available
    if not overall_health:
        candidates = [s for s in [arch_score, maint_score, debt_score, sec_score, cr_score] if s]
        overall_health = round(sum(candidates) / len(candidates), 1) if candidates else 70.0

    # Risk score = inverse of health (higher = riskier)
    risk_score = round(max(0.0, 100.0 - overall_health), 1)

    return EngineeringReportMetrics(
        overall_health_score   = overall_health,
        risk_score             = risk_score,
        security_score         = sec_score or cr_score,
        performance_score      = perf_score,
        architecture_score     = arch_score,
        maintainability_score  = maint_score,
        technical_debt_score   = debt_score,
        complexity_score       = complexity_score,
        documentation_score    = doc_score,
        testability_score      = test_score,
        confidence_score       = 1.0,
    )


def _findings_to_score(findings: List[Dict]) -> float:
    """Convert a list of severity-tagged findings to a 0-100 health score."""
    if not findings:
        return 0.0
    severity_penalty = {"critical": 20, "high": 10, "medium": 5, "low": 2, "info": 0}
    total_penalty = sum(severity_penalty.get((f.get("severity") or "info").lower(), 0) for f in findings)
    return round(max(0.0, min(100.0, 100.0 - total_penalty)), 1)


def _build_action_plan(
    code_review_findings:  List[Dict],
    security_findings:     List[Dict],
    performance_findings:  List[Dict],
    refactoring_findings:  List[Dict],
    architecture_findings: List[Dict],
) -> List[ActionItem]:
    """
    Build a prioritised action plan from critical and high severity findings
    across all agent outputs. Capped at 20 items sorted by priority weight.
    """
    PRIORITY_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    items: List[ActionItem] = []

    def _add(findings: List[Dict], category: str, agent: str):
        for f in findings:
            sev = (f.get("severity") or f.get("priority") or "medium").lower()
            if sev not in ("critical", "high", "medium"):
                continue
            title = (
                f.get("issue")
                or f.get("refactoring_type")
                or f.get("category")
                or "Finding"
            )
            desc = f.get("explanation") or f.get("description") or ""
            effort = float(f.get("estimated_effort_hours") or 1.0)
            items.append(ActionItem(
                priority               = sev,
                title                  = str(title)[:120],
                description            = str(desc)[:300],
                category               = category,
                estimated_effort_hours = effort,
                agent_source           = agent,
            ))

    _add(security_findings,     "security",      "security_review")
    _add(code_review_findings,  "code_review",   "code_review")
    _add(performance_findings,  "performance",   "performance")
    _add(refactoring_findings,  "refactoring",   "refactoring_analysis")
    _add(architecture_findings, "architecture",  "code_quality")

    # Sort by priority weight descending, then effort ascending
    items.sort(key=lambda x: (-PRIORITY_WEIGHT.get(x.priority, 0), x.estimated_effort_hours))
    return items[:20]
