"""
Unit Tests — ReportGeneratorAgent
===================================
Tests the LangGraph agent that aggregates prior agent outputs into a
structured EngineeringReportData payload.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import asdict

from src.application.agents.report_generator import (
    ReportGeneratorAgent,
    _build_metrics,
    _build_action_plan,
    _findings_to_score,
)
from src.domain.models.agents import AgentType


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_llm(content: str = "{}") -> MagicMock:
    llm = MagicMock()
    resp = MagicMock()
    resp.content = content
    llm.complete = AsyncMock(return_value=resp)
    return llm


def _security_findings():
    return [
        {"severity": "critical", "issue": "SQL Injection", "explanation": "Unsanitized input", "file_path": "api.py", "line_number": 42},
        {"severity": "high",     "issue": "Hardcoded secret", "explanation": "API key in source", "file_path": "config.py"},
        {"severity": "medium",   "issue": "Weak TLS config", "explanation": "TLS 1.0 enabled"},
    ]


def _perf_findings():
    return [
        {"severity": "high",   "issue": "N+1 query",   "suggested_optimization": "Use bulk fetch", "confidence_score": 0.9},
        {"severity": "medium", "issue": "No caching",  "suggested_optimization": "Add Redis cache"},
    ]


def _refactoring_findings():
    return [
        {"priority": "high",   "refactoring_type": "Extract method",    "category": "complexity",  "explanation": "200-line function", "estimated_effort_hours": 3.0},
        {"priority": "medium", "refactoring_type": "Rename variables",  "category": "naming",      "explanation": "Single-char vars",  "estimated_effort_hours": 1.0},
    ]


def _arch_findings():
    return [
        {"severity": "high",   "category": "layer_violation", "explanation": "Domain imports infra", "recommendation": "Use interface"},
        {"severity": "medium", "category": "coupling",        "explanation": "High coupling detected"},
    ]


def _quality_metrics():
    return {
        "overall_health_score": 72.5,
        "architecture_score":   75.0,
        "maintainability_score": 68.0,
        "technical_debt_score": 65.0,
        "complexity_score":     80.0,
        "documentation_score":  85.0,
        "testability_score":    78.0,
    }


LLM_RESPONSE = """{
  "executive_summary": "This repository shows moderate health with critical security issues.",
  "repository_overview": {"primary_languages": ["Python"], "primary_framework": "FastAPI"},
  "code_review_summary": "15 code quality issues found.",
  "security_summary": "3 security vulnerabilities including 1 critical SQL injection.",
  "performance_summary": "2 performance bottlenecks identified.",
  "refactoring_summary": "2 refactoring opportunities.",
  "architecture_summary": "2 architecture issues.",
  "tech_debt_summary": "Estimated 8h of technical debt.",
  "total_technical_debt_hours": 8.0,
  "tech_debt_breakdown": {"security": 2.0, "performance": 1.0, "refactoring": 3.0, "architecture": 2.0},
  "complexity_summary": "Moderate complexity.",
  "maintainability_summary": "Maintainability index is acceptable.",
  "risk_level": "high",
  "risk_summary": "High risk due to critical SQL injection vulnerability.",
  "risk_factors": ["SQL injection in api.py", "Hardcoded API key"],
  "future_improvements": ["Adopt parameterized queries", "Use secrets manager"],
  "future_improvements_summary": "Focus on security hardening first."
}"""


# ── _findings_to_score ────────────────────────────────────────────────────────

def test_findings_to_score_empty():
    assert _findings_to_score([]) == 0.0


def test_findings_to_score_critical_reduces_score():
    findings = [{"severity": "critical"}, {"severity": "critical"}, {"severity": "critical"}]
    score = _findings_to_score(findings)
    # 3 critical × 20 = 60 penalty → 40.0
    assert score == 40.0


def test_findings_to_score_bounded_zero():
    findings = [{"severity": "critical"}] * 10
    score = _findings_to_score(findings)
    assert score == 0.0


def test_findings_to_score_low_severity():
    findings = [{"severity": "low"}, {"severity": "info"}]
    score = _findings_to_score(findings)
    assert score == 98.0   # 100 - 2 - 0


# ── _build_metrics ────────────────────────────────────────────────────────────

def test_build_metrics_uses_quality_metrics():
    metrics = _build_metrics(
        quality_metrics      = _quality_metrics(),
        security_findings    = [],
        performance_out      = {},
        refactoring_out      = {},
        code_review_findings = [],
    )
    assert metrics.overall_health_score == 72.5
    assert metrics.architecture_score   == 75.0
    assert metrics.risk_score == round(100.0 - 72.5, 1)


def test_build_metrics_security_score_from_findings():
    metrics = _build_metrics(
        quality_metrics      = {},
        security_findings    = _security_findings(),
        performance_out      = {},
        refactoring_out      = {},
        code_review_findings = [],
    )
    # 1 critical (20) + 1 high (10) + 1 medium (5) = 35 penalty → 65.0
    assert metrics.security_score == 65.0


def test_build_metrics_fallback_health_when_no_quality_metrics():
    metrics = _build_metrics(
        quality_metrics      = {},
        security_findings    = _security_findings(),
        performance_out      = {},
        refactoring_out      = {},
        code_review_findings = [],
    )
    # health computed from available scores
    assert metrics.overall_health_score > 0


# ── _build_action_plan ────────────────────────────────────────────────────────

def test_build_action_plan_empty():
    items = _build_action_plan([], [], [], [], [])
    assert items == []


def test_build_action_plan_excludes_low():
    low_findings = [{"severity": "low", "issue": "Minor", "explanation": "Minor issue"}]
    items = _build_action_plan([], low_findings, [], [], [])
    assert items == []


def test_build_action_plan_includes_critical_and_high():
    items = _build_action_plan(
        code_review_findings  = [],
        security_findings     = _security_findings(),
        performance_findings  = _perf_findings(),
        refactoring_findings  = _refactoring_findings(),
        architecture_findings = _arch_findings(),
    )
    priorities = {i.priority for i in items}
    assert "critical" in priorities or "high" in priorities


def test_build_action_plan_sorted_by_priority():
    items = _build_action_plan(
        code_review_findings  = [],
        security_findings     = _security_findings(),
        performance_findings  = [],
        refactoring_findings  = [],
        architecture_findings = [],
    )
    if len(items) >= 2:
        priority_order = {"critical": 4, "high": 3, "medium": 2}
        for i in range(len(items) - 1):
            assert (priority_order.get(items[i].priority, 0)
                    >= priority_order.get(items[i + 1].priority, 0))


def test_build_action_plan_capped_at_20():
    many = [{"severity": "critical", "issue": f"Issue {i}", "explanation": "Detail"} for i in range(50)]
    items = _build_action_plan([], many, many, [], [])
    assert len(items) <= 20


# ── ReportGeneratorAgent.execute ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_returns_agent_outputs():
    llm = _make_llm(LLM_RESPONSE)
    agent = ReportGeneratorAgent(llm)

    state = {
        "query":   "Generate engineering report",
        "repo_id": "repo-123",
        "agent_outputs": {
            AgentType.SECURITY_REVIEW.value:     {"structured_findings": _security_findings()},
            AgentType.PERFORMANCE.value:         {"structured_findings": _perf_findings(), "performance_score": 65.0},
            AgentType.REFACTORING_ANALYSIS.value:{"structured_findings": _refactoring_findings()},
            AgentType.CODE_QUALITY.value:        {"structured_findings": _arch_findings(), "metrics": _quality_metrics(), "dependency_analysis": {}},
            AgentType.CODE_REVIEW.value:         {"structured_findings": []},
        },
        "pending_tasks":  [AgentType.REPORT_GENERATION.value],
        "completed_tasks": [],
    }

    result = await agent.execute(state)

    assert AgentType.REPORT_GENERATION.value in result["agent_outputs"]
    output = result["agent_outputs"][AgentType.REPORT_GENERATION.value]
    assert "report_data" in output
    assert "metrics" in output
    assert output["risk_level"] in ("critical", "high", "medium", "low")
    assert AgentType.REPORT_GENERATION.value not in result["pending_tasks"]
    assert AgentType.REPORT_GENERATION.value in result["completed_tasks"]


@pytest.mark.asyncio
async def test_execute_handles_llm_json_error():
    llm = _make_llm("not valid json {{{{")
    agent = ReportGeneratorAgent(llm)

    state = {
        "query":   "Generate report",
        "repo_id": "repo-xyz",
        "agent_outputs": {},
        "pending_tasks":  [AgentType.REPORT_GENERATION.value],
        "completed_tasks": [],
    }

    # Should NOT raise — graceful degradation
    result = await agent.execute(state)
    assert AgentType.REPORT_GENERATION.value in result["agent_outputs"]


@pytest.mark.asyncio
async def test_execute_strips_markdown_fences():
    content = "```json\n" + LLM_RESPONSE + "\n```"
    llm = _make_llm(content)
    agent = ReportGeneratorAgent(llm)

    state = {
        "query": "report", "repo_id": "r",
        "agent_outputs": {}, "pending_tasks": [AgentType.REPORT_GENERATION.value],
        "completed_tasks": [],
    }
    result = await agent.execute(state)
    output = result["agent_outputs"][AgentType.REPORT_GENERATION.value]
    rd = output["report_data"]
    assert rd["executive_summary"] != ""


@pytest.mark.asyncio
async def test_execute_traces_recorded():
    llm = _make_llm(LLM_RESPONSE)
    agent = ReportGeneratorAgent(llm)

    state = {
        "query": "report", "repo_id": "r",
        "agent_outputs": {}, "pending_tasks": [AgentType.REPORT_GENERATION.value],
        "completed_tasks": [],
    }
    result = await agent.execute(state)
    trace = result.get("execution_trace", [])
    assert len(trace) == 1
    assert trace[0]["agent"] == AgentType.REPORT_GENERATION.value
    assert "latency_ms" in trace[0]
