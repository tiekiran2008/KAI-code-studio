"""
Engineering Report Domain Entities
===================================
Domain models for the AI Engineering Report Generator (Phase 11.6).
Covers report sections, export formats, overall metrics, and the
complete structured report payload.

IMPORTANT: This module is advisory only. Reports are generated from
           existing agent outputs and NEVER modify source code.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class ExportFormatEnum(str, Enum):
    """Supported report export formats."""
    PDF       = "pdf"
    HTML      = "html"
    MARKDOWN  = "markdown"
    JSON      = "json"
    SARIF     = "sarif"


class ReportStatusEnum(str, Enum):
    PENDING    = "pending"
    GENERATING = "generating"
    COMPLETED  = "completed"
    FAILED     = "failed"


class ReportSectionEnum(str, Enum):
    EXECUTIVE_SUMMARY           = "executive_summary"
    REPOSITORY_OVERVIEW         = "repository_overview"
    CODE_REVIEW_SUMMARY         = "code_review_summary"
    SECURITY_FINDINGS           = "security_findings"
    PERFORMANCE_FINDINGS        = "performance_findings"
    REFACTORING_RECOMMENDATIONS = "refactoring_recommendations"
    ARCHITECTURE_ASSESSMENT     = "architecture_assessment"
    HEALTH_METRICS              = "health_metrics"
    TECH_DEBT_SUMMARY           = "tech_debt_summary"
    COMPLEXITY_ANALYSIS         = "complexity_analysis"
    MAINTAINABILITY_ANALYSIS    = "maintainability_analysis"
    HOTSPOT_FILES               = "hotspot_files"
    RISK_ASSESSMENT             = "risk_assessment"
    PRIORITY_ACTION_PLAN        = "priority_action_plan"
    FUTURE_IMPROVEMENTS         = "future_improvements"


@dataclass
class EngineeringReportMetrics:
    """Aggregated numeric scores from all analysis agents (0–100)."""
    overall_health_score:         float = 0.0
    risk_score:                   float = 0.0   # Higher = more risky
    security_score:               float = 0.0
    performance_score:            float = 0.0
    architecture_score:           float = 0.0
    maintainability_score:        float = 0.0
    technical_debt_score:         float = 0.0
    complexity_score:             float = 0.0
    documentation_score:          float = 0.0
    testability_score:            float = 0.0
    # Composite / derived
    confidence_score:             float = 1.0


@dataclass
class ActionItem:
    priority: str        # critical | high | medium | low
    title: str
    description: str
    category: str        # security | performance | refactoring | architecture | …
    estimated_effort_hours: float = 0.0
    agent_source: str = ""


@dataclass
class EngineeringReportData:
    """
    Complete structured payload for a generated engineering report.
    All 15 sections map to the report sections defined by ReportSectionEnum.
    """
    # ── Meta ──────────────────────────────────────────────────────────────
    report_id:         str = ""
    review_id:         str = ""
    repository_id:     str = ""
    repository_name:   str = ""
    generated_at:      str = ""
    report_version:    str = "1.0"

    # ── Section 1 – Executive Summary ─────────────────────────────────────
    executive_summary: str = ""

    # ── Section 2 – Repository Overview ──────────────────────────────────
    repository_overview: Dict[str, Any] = field(default_factory=dict)
    # keys: languages, total_files, total_lines, primary_framework, tech_stack, age_days

    # ── Section 3 – Code Review Summary ──────────────────────────────────
    code_review_findings:   List[Dict[str, Any]] = field(default_factory=list)
    code_review_summary:    str = ""

    # ── Section 4 – Security Findings ─────────────────────────────────────
    security_findings:      List[Dict[str, Any]] = field(default_factory=list)
    security_summary:       str = ""

    # ── Section 5 – Performance Findings ──────────────────────────────────
    performance_findings:         List[Dict[str, Any]] = field(default_factory=list)
    performance_recommendations:  List[Dict[str, Any]] = field(default_factory=list)
    performance_summary:          str = ""

    # ── Section 6 – Refactoring Recommendations ────────────────────────────
    refactoring_findings:   List[Dict[str, Any]] = field(default_factory=list)
    refactoring_summary:    str = ""

    # ── Section 7 – Architecture Assessment ──────────────────────────────
    architecture_findings:  List[Dict[str, Any]] = field(default_factory=list)
    dependency_analysis:    Dict[str, Any] = field(default_factory=dict)
    architecture_summary:   str = ""

    # ── Section 8 – Health Metrics ────────────────────────────────────────
    metrics: EngineeringReportMetrics = field(default_factory=EngineeringReportMetrics)

    # ── Section 9 – Technical Debt Summary ────────────────────────────────
    total_technical_debt_hours:  float = 0.0
    tech_debt_breakdown:         Dict[str, float] = field(default_factory=dict)
    tech_debt_summary:           str = ""

    # ── Section 10 – Complexity Analysis ──────────────────────────────────
    complexity_hotspots:  List[Dict[str, Any]] = field(default_factory=list)
    complexity_summary:   str = ""

    # ── Section 11 – Maintainability Analysis ─────────────────────────────
    maintainability_issues:  List[Dict[str, Any]] = field(default_factory=list)
    maintainability_summary: str = ""

    # ── Section 12 – Hotspot Files ────────────────────────────────────────
    hotspot_files:  List[Dict[str, Any]] = field(default_factory=list)

    # ── Section 13 – Risk Assessment ──────────────────────────────────────
    risk_level:    str = "medium"   # critical | high | medium | low
    risk_factors:  List[str] = field(default_factory=list)
    risk_summary:  str = ""

    # ── Section 14 – Priority Action Plan ─────────────────────────────────
    action_items:  List[ActionItem] = field(default_factory=list)

    # ── Section 15 – Future Improvements ──────────────────────────────────
    future_improvements: List[str] = field(default_factory=list)
    future_improvements_summary: str = ""
