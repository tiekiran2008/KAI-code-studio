"""
Multi-Format Report Exporter
=============================
Converts an EngineeringReportData payload into:
  - Markdown  (.md)
  - Standalone HTML  (.html)
  - JSON  (.json)
  - SARIF v2.1.0  (.sarif)
  - PDF  (.pdf)  — via WeasyPrint (optional) or falls back to HTML
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.report_entity import EngineeringReportData

# ── SARIF v2.1.0 schema URI ───────────────────────────────────────────────────
_SARIF_SCHEMA = "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json"
_SARIF_VERSION = "2.1.0"

# ── Severity → SARIF level mapping ───────────────────────────────────────────
_SEV_TO_SARIF = {
    "critical": "error",
    "high":     "error",
    "medium":   "warning",
    "low":      "note",
    "info":     "note",
}


class ReportExporter:
    """Converts EngineeringReportData to multiple export formats."""

    # ──────────────────────────────────────────────────────────────────────
    # Public interface
    # ──────────────────────────────────────────────────────────────────────

    def to_markdown(self, report: "EngineeringReportData") -> str:
        """Render the report as GitHub-flavoured Markdown."""
        m = report.metrics
        lines: list[str] = []

        lines += [
            f"# Engineering Report — {report.repository_name or report.repository_id}",
            f"> Generated: {report.generated_at}  |  Version: {report.report_version}",
            f"> Review ID: `{report.review_id}`  |  Report ID: `{report.report_id}`",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            "",
            report.executive_summary or "_No summary generated._",
            "",
        ]

        # ── Health Metrics table ──────────────────────────────────────────
        lines += [
            "## 2. Health Metrics",
            "",
            "| Metric | Score |",
            "|--------|-------|",
            f"| 🏥 Overall Health    | {m.overall_health_score:.1f} / 100 |",
            f"| 🔴 Risk              | {m.risk_score:.1f} / 100 |",
            f"| 🛡️ Security          | {m.security_score:.1f} / 100 |",
            f"| ⚡ Performance       | {m.performance_score:.1f} / 100 |",
            f"| 🏛️ Architecture      | {m.architecture_score:.1f} / 100 |",
            f"| 🔧 Maintainability   | {m.maintainability_score:.1f} / 100 |",
            f"| 🏦 Technical Debt    | {m.technical_debt_score:.1f} / 100 |",
            f"| 🧠 Complexity        | {m.complexity_score:.1f} / 100 |",
            f"| 📝 Documentation     | {m.documentation_score:.1f} / 100 |",
            f"| 🧪 Testability       | {m.testability_score:.1f} / 100 |",
            "",
        ]

        # ── Risk Assessment ────────────────────────────────────────────────
        lines += [
            f"## 3. Risk Assessment — **{report.risk_level.upper()}**",
            "",
            report.risk_summary or "",
            "",
        ]
        if report.risk_factors:
            lines.append("**Risk Factors:**")
            for rf in report.risk_factors:
                lines.append(f"- {rf}")
            lines.append("")

        # ── Priority Action Plan ───────────────────────────────────────────
        lines += ["## 4. Priority Action Plan", ""]
        if report.action_items:
            lines += ["| Priority | Category | Title | Effort (hrs) |",
                      "|----------|----------|-------|-------------|"]
            for item in report.action_items:
                prio   = getattr(item, "priority", "") if not isinstance(item, dict) else item.get("priority", "")
                cat    = getattr(item, "category", "") if not isinstance(item, dict) else item.get("category", "")
                title  = getattr(item, "title", "") if not isinstance(item, dict) else item.get("title", "")
                effort = getattr(item, "estimated_effort_hours", 0.0) if not isinstance(item, dict) else item.get("estimated_effort_hours", 0.0)
                lines.append(
                    f"| {str(prio).upper()} | {cat} | {title} | {float(effort):.1f} |"
                )
            lines.append("")
        else:
            lines += ["_No priority actions identified._", ""]

        # ── Code Review Summary ────────────────────────────────────────────
        lines += [
            "## 5. Code Review Summary",
            "",
            report.code_review_summary or "_No code review findings._",
            f"**Total Findings:** {len(report.code_review_findings)}",
            "",
        ]

        # ── Security Findings ──────────────────────────────────────────────
        lines += [
            "## 6. Security Findings",
            "",
            report.security_summary or "_No security findings._",
            f"**Total Security Issues:** {len(report.security_findings)}",
            "",
        ]
        for i, f in enumerate(report.security_findings[:15], 1):
            sev = f.get("severity", "info").upper()
            lines.append(f"### [{sev}] {f.get('issue', f.get('title', 'Issue'))} (#{i})")
            if f.get("file_path"):
                lines.append(f"- **File:** `{f['file_path']}`:{f.get('line_number', '')}")
            if f.get("explanation"):
                lines.append(f"- **Detail:** {f['explanation']}")
            lines.append("")

        # ── Performance Findings ───────────────────────────────────────────
        lines += [
            "## 7. Performance Findings",
            "",
            report.performance_summary or "_No performance findings._",
            f"**Total Performance Issues:** {len(report.performance_findings)}",
            "",
        ]

        # ── Refactoring Recommendations ────────────────────────────────────
        lines += [
            "## 8. Refactoring Recommendations",
            "",
            report.refactoring_summary or "_No refactoring recommendations._",
            f"**Total Refactoring Suggestions:** {len(report.refactoring_findings)}",
            "",
        ]

        # ── Architecture Assessment ────────────────────────────────────────
        lines += [
            "## 9. Architecture Assessment",
            "",
            report.architecture_summary or "_No architecture findings._",
            f"**Total Architecture Issues:** {len(report.architecture_findings)}",
            "",
        ]

        # ── Technical Debt ─────────────────────────────────────────────────
        lines += [
            "## 10. Technical Debt Summary",
            "",
            report.tech_debt_summary or "",
            f"**Total Estimated Debt:** {report.total_technical_debt_hours:.1f} hours",
            "",
        ]

        # ── Hotspot Files ──────────────────────────────────────────────────
        if report.hotspot_files:
            lines += ["## 11. Hotspot Files", "",
                      "| File | Complexity Score | Debt (hrs) | Issues |",
                      "|------|-----------------|------------|--------|"]
            for h in report.hotspot_files[:10]:
                lines.append(
                    f"| `{h.get('file_path', '')}` | {h.get('complexity_score', 0):.1f} "
                    f"| {h.get('technical_debt_hours', 0):.1f} | {h.get('issue_count', 0)} |"
                )
            lines.append("")

        # ── Future Improvements ────────────────────────────────────────────
        lines += ["## 12. Future Improvements", ""]
        if report.future_improvements:
            for fi in report.future_improvements:
                lines.append(f"- {fi}")
        lines.append("")

        return "\n".join(lines)

    def to_html(self, report: "EngineeringReportData") -> str:
        """Render the report as a self-contained dark-mode HTML file."""
        md_content = self.to_markdown(report)
        # Convert simple Markdown to HTML (no external deps required)
        body = self._md_to_html(md_content)
        m = report.metrics

        gauge_rows = [
            ("Overall Health", m.overall_health_score, "#6ee7b7"),
            ("Security",       m.security_score,       "#f87171"),
            ("Performance",    m.performance_score,    "#fbbf24"),
            ("Architecture",   m.architecture_score,   "#818cf8"),
            ("Maintainability",m.maintainability_score,"#34d399"),
            ("Tech Debt",      m.technical_debt_score, "#fb923c"),
            ("Complexity",     m.complexity_score,     "#a78bfa"),
            ("Documentation",  m.documentation_score,  "#38bdf8"),
            ("Testability",    m.testability_score,    "#4ade80"),
        ]

        gauges_html = "".join([
            f"""
            <div class="gauge-item">
              <div class="gauge-label">{label}</div>
              <div class="gauge-track">
                <div class="gauge-fill" style="width:{min(score,100):.1f}%;background:{color};"></div>
              </div>
              <div class="gauge-value">{score:.1f}</div>
            </div>"""
            for label, score, color in gauge_rows
        ])

        risk_color = {"critical": "#f87171", "high": "#fb923c", "medium": "#fbbf24", "low": "#4ade80"}.get(
            report.risk_level, "#94a3b8"
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Engineering Report — {report.repository_name or report.repository_id}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:ui-sans-serif,system-ui,sans-serif;background:#0f172a;color:#e2e8f0;line-height:1.7;padding:2rem}}
  .container{{max-width:960px;margin:0 auto}}
  h1{{font-size:2rem;font-weight:800;color:#f8fafc;margin-bottom:.25rem}}
  h2{{font-size:1.25rem;font-weight:700;color:#c7d2fe;margin:2rem 0 .75rem;border-bottom:1px solid #1e293b;padding-bottom:.5rem}}
  h3{{font-size:1rem;font-weight:600;color:#93c5fd;margin:1rem 0 .25rem}}
  p,li{{color:#cbd5e1;font-size:.9rem}}
  ul,ol{{padding-left:1.5rem;margin:.5rem 0}}
  code{{background:#1e293b;padding:.1rem .35rem;border-radius:.25rem;font-family:monospace;font-size:.82rem;color:#a5f3fc}}
  pre{{background:#1e293b;padding:1rem;border-radius:.5rem;overflow-x:auto;font-size:.82rem;color:#a5f3fc}}
  table{{width:100%;border-collapse:collapse;margin:.75rem 0;font-size:.85rem}}
  th{{background:#1e293b;color:#94a3b8;padding:.5rem .75rem;text-align:left;font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}}
  td{{padding:.5rem .75rem;border-bottom:1px solid #1e293b;color:#cbd5e1}}
  tr:hover td{{background:#1e293b40}}
  .meta{{color:#64748b;font-size:.8rem;margin-bottom:2rem}}
  .risk-badge{{display:inline-block;padding:.2rem .75rem;border-radius:9999px;font-weight:700;font-size:.85rem;background:{risk_color}22;color:{risk_color};border:1px solid {risk_color}44}}
  .gauges{{display:flex;flex-direction:column;gap:.5rem;margin:1rem 0 1.5rem}}
  .gauge-item{{display:flex;align-items:center;gap:1rem}}
  .gauge-label{{width:140px;font-size:.8rem;color:#94a3b8;text-align:right;flex-shrink:0}}
  .gauge-track{{flex:1;background:#1e293b;border-radius:9999px;height:10px;overflow:hidden}}
  .gauge-fill{{height:100%;border-radius:9999px;transition:width .5s ease}}
  .gauge-value{{width:48px;font-size:.8rem;font-weight:700;color:#f8fafc;text-align:right;font-family:monospace}}
  hr{{border:none;border-top:1px solid #1e293b;margin:2rem 0}}
  blockquote{{border-left:3px solid #6366f1;padding:.5rem 1rem;background:#1e293b44;border-radius:.25rem;color:#94a3b8;font-size:.85rem;margin:.5rem 0}}
  a{{color:#818cf8}}
</style>
</head>
<body>
<div class="container">
  <h1>Engineering Report</h1>
  <p class="meta">
    Repository: <strong>{report.repository_name or report.repository_id}</strong> &nbsp;|&nbsp;
    Generated: {report.generated_at} &nbsp;|&nbsp;
    Version: {report.report_version} &nbsp;|&nbsp;
    Risk Level: <span class="risk-badge">{report.risk_level.upper()}</span>
  </p>
  <h2>Health Metrics</h2>
  <div class="gauges">{gauges_html}</div>
  {body}
</div>
</body>
</html>"""

    def to_json(self, report: "EngineeringReportData") -> str:
        """Serialize the full report as pretty-printed JSON."""
        from dataclasses import asdict as _asdict
        return json.dumps(_asdict(report), indent=2, default=str)

    def to_sarif(self, report: "EngineeringReportData") -> str:
        """
        Emit a SARIF v2.1.0 document covering security, performance,
        refactoring, and architecture findings.
        """
        rules: list[dict] = []
        results: list[dict] = []
        rule_ids: set[str] = set()

        finding_groups = [
            ("SEC", report.security_findings,      "security"),
            ("PERF", report.performance_findings,  "performance"),
            ("REF", report.refactoring_findings,   "refactoring"),
            ("ARCH", report.architecture_findings, "architecture"),
        ]

        for prefix, findings, category in finding_groups:
            for idx, f in enumerate(findings):
                rule_id = f"{prefix}{idx:04d}"
                issue   = f.get("issue") or f.get("refactoring_type") or f.get("category") or "Finding"
                severity = f.get("severity") or f.get("priority") or "info"
                sarif_level = _SEV_TO_SARIF.get(severity.lower(), "note")
                explanation = f.get("explanation") or f.get("description") or ""
                file_path = f.get("file_path") or ""
                line_num  = f.get("line_number") or 1

                if rule_id not in rule_ids:
                    rule_ids.add(rule_id)
                    rules.append({
                        "id": rule_id,
                        "name": re.sub(r"\W+", "_", issue)[:64],
                        "shortDescription": {"text": issue[:255]},
                        "fullDescription": {"text": explanation[:1000]},
                        "helpUri": "",
                        "properties": {"category": category, "severity": severity},
                    })

                result: dict = {
                    "ruleId": rule_id,
                    "level": sarif_level,
                    "message": {"text": explanation or issue},
                }
                if file_path:
                    result["locations"] = [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": file_path},
                            "region": {"startLine": int(line_num)},
                        }
                    }]
                results.append(result)

        sarif_doc = {
            "$schema": _SARIF_SCHEMA,
            "version": _SARIF_VERSION,
            "runs": [{
                "tool": {
                    "driver": {
                        "name":            "AI Engineering Report Generator",
                        "version":         report.report_version,
                        "informationUri":  "",
                        "rules":           rules,
                    }
                },
                "results":   results,
                "artifacts": [{"location": {"uri": report.repository_id}}],
                "properties": {
                    "reportId":      report.report_id,
                    "repositoryId":  report.repository_id,
                    "generatedAt":   report.generated_at,
                    "overallHealth": report.metrics.overall_health_score,
                    "riskLevel":     report.risk_level,
                },
            }],
        }
        return json.dumps(sarif_doc, indent=2)

    def to_pdf(self, report: "EngineeringReportData") -> bytes:
        """
        Render a PDF using WeasyPrint if available.
        Falls back to returning the HTML bytes (UTF-8 encoded) otherwise.
        """
        html_str = self.to_html(report)
        try:
            from weasyprint import HTML  # type: ignore
            return HTML(string=html_str).write_pdf()
        except ImportError:
            # WeasyPrint not installed — return HTML bytes as fallback
            return html_str.encode("utf-8")

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _md_to_html(md: str) -> str:
        """
        Minimal Markdown → HTML conversion for the report body.
        Handles: headings, bold, code, tables, list items, blockquotes, HR, paragraphs.
        """
        lines = md.splitlines()
        html_lines: list[str] = []
        i = 0
        in_table = False
        in_list  = False

        def _inline(text: str) -> str:
            # Code spans
            text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
            # Bold
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            # Italic
            text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
            return text

        while i < len(lines):
            line = lines[i]

            # HR
            if re.match(r"^---+$", line.strip()):
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                html_lines.append("<hr>"); i += 1; continue

            # Headings
            m = re.match(r"^(#{1,4})\s+(.+)$", line)
            if m:
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                level = len(m.group(1))
                html_lines.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
                i += 1; continue

            # Blockquote
            if line.startswith(">"):
                if in_list:
                    html_lines.append("</ul>"); in_list = False
                content = line.lstrip("> ")
                html_lines.append(f"<blockquote>{_inline(content)}</blockquote>")
                i += 1; continue

            # Table row
            if "|" in line:
                if not in_table:
                    html_lines.append("<table><thead>"); in_table = True
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    html_lines.append("<tr>" + "".join(f"<th>{_inline(c)}</th>" for c in cells) + "</tr>")
                    html_lines.append("</thead><tbody>")
                    i += 2; continue  # skip separator row
                cells = [c.strip() for c in line.strip("|").split("|")]
                html_lines.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
                i += 1; continue
            elif in_table:
                html_lines.append("</tbody></table>"); in_table = False

            # List item
            m_li = re.match(r"^[-*]\s+(.+)$", line)
            if m_li:
                if not in_list:
                    html_lines.append("<ul>"); in_list = True
                html_lines.append(f"<li>{_inline(m_li.group(1))}</li>")
                i += 1; continue
            elif in_list and line.strip() == "":
                html_lines.append("</ul>"); in_list = False

            # Empty line → paragraph break
            if line.strip() == "":
                html_lines.append("")
            else:
                html_lines.append(f"<p>{_inline(line)}</p>")
            i += 1

        if in_list:
            html_lines.append("</ul>")
        if in_table:
            html_lines.append("</tbody></table>")

        return "\n".join(html_lines)
