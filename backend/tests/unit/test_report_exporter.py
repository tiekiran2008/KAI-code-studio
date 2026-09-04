"""
Unit Tests — ReportExporter
============================
Tests that each export format produces valid, well-formed output.
"""
import json
import pytest

from src.application.services.report_exporter import ReportExporter
from src.domain.entities.report_entity import (
    EngineeringReportData,
    EngineeringReportMetrics,
    ActionItem,
)

_SARIF_SCHEMA = "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json"


def _make_report() -> EngineeringReportData:
    metrics = EngineeringReportMetrics(
        overall_health_score  = 72.5,
        risk_score            = 27.5,
        security_score        = 65.0,
        performance_score     = 70.0,
        architecture_score    = 75.0,
        maintainability_score = 68.0,
        technical_debt_score  = 65.0,
        complexity_score      = 80.0,
        documentation_score   = 85.0,
        testability_score     = 78.0,
        confidence_score      = 0.92,
    )
    return EngineeringReportData(
        report_id            = "rpt-001",
        review_id            = "rev-001",
        repository_id        = "repo-123",
        repository_name      = "my-service",
        generated_at         = "2026-08-05T14:00:00Z",
        report_version       = "1.0",
        executive_summary    = "Overall health is moderate with critical security issues.",
        repository_overview  = {"primary_languages": ["Python"], "primary_framework": "FastAPI"},
        code_review_findings = [{"severity": "high", "issue": "Missing error handling", "explanation": "Function raises uncaught exception", "confidence_score": 0.9}],
        code_review_summary  = "1 high severity code issue found.",
        security_findings    = [
            {"severity": "critical", "issue": "SQL Injection", "explanation": "Unsanitised input", "file_path": "api.py", "line_number": 42},
            {"severity": "high",     "issue": "Hardcoded secret", "explanation": "API key in source", "file_path": "config.py", "line_number": 10},
        ],
        security_summary     = "2 security issues found including 1 critical.",
        performance_findings = [{"severity": "high", "issue": "N+1 query", "explanation": "Loop DB calls", "file_path": "orm.py", "line_number": 88}],
        performance_summary  = "1 performance bottleneck.",
        refactoring_findings = [{"priority": "high", "refactoring_type": "Extract method", "category": "complexity", "explanation": "200-line function", "estimated_effort_hours": 3.0}],
        refactoring_summary  = "1 refactoring opportunity.",
        architecture_findings= [{"severity": "medium", "category": "layer_violation", "explanation": "Domain imports infra", "recommendation": "Use interface"}],
        architecture_summary = "1 architecture issue.",
        metrics              = metrics,
        total_technical_debt_hours = 12.5,
        tech_debt_breakdown  = {"security": 4.0, "performance": 2.0, "refactoring": 3.0, "architecture": 3.5},
        tech_debt_summary    = "Estimated 12.5h of technical debt across 4 categories.",
        hotspot_files        = [{"file_path": "api.py", "complexity_score": 88.0, "technical_debt_hours": 5.0, "issue_count": 4}],
        risk_level           = "high",
        risk_factors         = ["SQL injection in api.py", "Hardcoded API key"],
        risk_summary         = "High risk due to critical security vulnerability.",
        action_items         = [
            ActionItem(priority="critical", title="Fix SQL Injection", description="Parameterize all queries.", category="security", estimated_effort_hours=2.0, agent_source="security_review"),
            ActionItem(priority="high", title="Extract large method", description="Break up 200-line function.", category="refactoring", estimated_effort_hours=3.0, agent_source="refactoring_analysis"),
        ],
        future_improvements  = ["Adopt parameterized queries", "Integrate SAST in CI/CD"],
        future_improvements_summary = "Prioritise security hardening, then refactoring.",
    )


@pytest.fixture()
def exporter():
    return ReportExporter()


@pytest.fixture()
def report():
    return _make_report()


# ── Markdown ──────────────────────────────────────────────────────────────────

class TestMarkdownExport:
    def test_returns_string(self, exporter, report):
        md = exporter.to_markdown(report)
        assert isinstance(md, str)

    def test_contains_repository_name(self, exporter, report):
        md = exporter.to_markdown(report)
        assert "my-service" in md

    def test_contains_executive_summary(self, exporter, report):
        md = exporter.to_markdown(report)
        assert "Overall health is moderate" in md

    def test_contains_health_metrics_section(self, exporter, report):
        md = exporter.to_markdown(report)
        assert "Health Metrics" in md
        assert "72.5" in md   # overall_health_score

    def test_contains_action_plan(self, exporter, report):
        md = exporter.to_markdown(report)
        assert "Fix SQL Injection" in md

    def test_contains_tech_debt(self, exporter, report):
        md = exporter.to_markdown(report)
        assert "12.5" in md

    def test_contains_hotspot_files(self, exporter, report):
        md = exporter.to_markdown(report)
        assert "api.py" in md

    def test_contains_future_improvements(self, exporter, report):
        md = exporter.to_markdown(report)
        assert "Adopt parameterized queries" in md


# ── HTML ──────────────────────────────────────────────────────────────────────

class TestHTMLExport:
    def test_returns_string(self, exporter, report):
        html = exporter.to_html(report)
        assert isinstance(html, str)

    def test_valid_html_structure(self, exporter, report):
        html = exporter.to_html(report)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_dark_mode_styles_present(self, exporter, report):
        html = exporter.to_html(report)
        assert "background:#0f172a" in html or "background: #0f172a" in html or "#0f172a" in html

    def test_risk_level_badge_present(self, exporter, report):
        html = exporter.to_html(report)
        assert "HIGH" in html

    def test_gauge_bars_present(self, exporter, report):
        html = exporter.to_html(report)
        assert "gauge-fill" in html
        assert "Overall Health" in html

    def test_repository_name_in_title(self, exporter, report):
        html = exporter.to_html(report)
        assert "my-service" in html


# ── JSON ──────────────────────────────────────────────────────────────────────

class TestJSONExport:
    def test_returns_valid_json_string(self, exporter, report):
        result = exporter.to_json(report)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_all_top_level_fields_present(self, exporter, report):
        parsed = json.loads(exporter.to_json(report))
        assert parsed["report_id"]       == "rpt-001"
        assert parsed["repository_id"]   == "repo-123"
        assert parsed["risk_level"]      == "high"

    def test_metrics_serialised(self, exporter, report):
        parsed = json.loads(exporter.to_json(report))
        m = parsed["metrics"]
        assert m["overall_health_score"] == 72.5

    def test_findings_lists_serialised(self, exporter, report):
        parsed = json.loads(exporter.to_json(report))
        assert len(parsed["security_findings"])    == 2
        assert len(parsed["performance_findings"]) == 1
        assert len(parsed["refactoring_findings"]) == 1

    def test_action_items_serialised(self, exporter, report):
        parsed = json.loads(exporter.to_json(report))
        items = parsed["action_items"]
        assert len(items) == 2
        assert items[0]["title"] == "Fix SQL Injection"


# ── SARIF ─────────────────────────────────────────────────────────────────────

class TestSARIFExport:
    def test_returns_valid_json(self, exporter, report):
        sarif_str = exporter.to_sarif(report)
        doc = json.loads(sarif_str)
        assert isinstance(doc, dict)

    def test_sarif_version(self, exporter, report):
        doc = json.loads(exporter.to_sarif(report))
        assert doc["version"] == "2.1.0"

    def test_sarif_schema(self, exporter, report):
        doc = json.loads(exporter.to_sarif(report))
        assert doc["$schema"] == _SARIF_SCHEMA

    def test_runs_block_present(self, exporter, report):
        doc = json.loads(exporter.to_sarif(report))
        assert "runs" in doc
        assert len(doc["runs"]) == 1

    def test_tool_driver_name(self, exporter, report):
        doc = json.loads(exporter.to_sarif(report))
        driver = doc["runs"][0]["tool"]["driver"]
        assert driver["name"] == "AI Engineering Report Generator"

    def test_results_contain_all_findings(self, exporter, report):
        doc = json.loads(exporter.to_sarif(report))
        results = doc["runs"][0]["results"]
        # 2 security + 1 performance + 1 refactoring + 1 architecture = 5
        assert len(results) == 5

    def test_critical_maps_to_error_level(self, exporter, report):
        doc = json.loads(exporter.to_sarif(report))
        results = doc["runs"][0]["results"]
        error_levels = [r["level"] for r in results]
        assert "error" in error_levels

    def test_location_physical_uri_set(self, exporter, report):
        doc = json.loads(exporter.to_sarif(report))
        results = doc["runs"][0]["results"]
        # First result (SQL Injection) has file_path = "api.py"
        loc = results[0]["locations"][0]["physicalLocation"]
        assert loc["artifactLocation"]["uri"] == "api.py"
        assert loc["region"]["startLine"] == 42

    def test_rules_match_results(self, exporter, report):
        doc = json.loads(exporter.to_sarif(report))
        run = doc["runs"][0]
        rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
        result_rule_ids = {r["ruleId"] for r in run["results"]}
        assert result_rule_ids.issubset(rule_ids)

    def test_report_properties_in_run(self, exporter, report):
        doc = json.loads(exporter.to_sarif(report))
        props = doc["runs"][0]["properties"]
        assert props["riskLevel"] == "high"
        assert props["overallHealth"] == 72.5


# ── PDF (fallback) ────────────────────────────────────────────────────────────

class TestPDFExport:
    def test_returns_bytes(self, exporter, report):
        result = exporter.to_pdf(report)
        assert isinstance(result, bytes)

    def test_fallback_contains_html(self, exporter, report):
        # Without WeasyPrint installed, should return HTML bytes
        try:
            import weasyprint  # type: ignore
            # If available, should return PDF header
            assert result[:4] == b"%PDF" or len(result) > 0
        except ImportError:
            result = exporter.to_pdf(report)
            content = result.decode("utf-8", errors="ignore")
            assert "<!DOCTYPE html>" in content
