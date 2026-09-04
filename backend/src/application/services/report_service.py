"""
Report Application Service
===========================
Manages engineering report lifecycle: creation, retrieval, listing,
comparison, and delegating export to ReportExporter.
"""
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from src.infrastructure.repositories.report_repository import ReportRepository
from src.infrastructure.persistence.report_models import DBReport
from src.domain.entities.report_entity import (
    EngineeringReportData,
    EngineeringReportMetrics,
    ActionItem,
    ReportStatusEnum,
    ExportFormatEnum,
)
from src.application.services.report_exporter import ReportExporter
from src.core.logger import logger


class ReportService:
    """Application service for the Engineering Report Generator."""

    def __init__(self, repository: ReportRepository) -> None:
        self.repo     = repository
        self.exporter = ReportExporter()

    # ── Persistence helpers ────────────────────────────────────────────────

    def create_report_record(
        self,
        user_id: str,
        repository_id: str,
        review_id: Optional[str] = None,
        title: str = "Engineering Report",
    ) -> DBReport:
        report_id = str(uuid.uuid4())
        db_report = DBReport(
            id            = report_id,
            repository_id = repository_id,
            review_id     = review_id,
            user_id       = user_id,
            title         = title,
            status        = ReportStatusEnum.PENDING.value,
        )
        return self.repo.create(db_report)

    def save_report_data(
        self,
        report_id: str,
        report_data: EngineeringReportData,
    ) -> Optional[DBReport]:
        m = report_data.metrics
        return self.repo.update_content(
            report_id,
            status                  = ReportStatusEnum.COMPLETED.value,
            report_content_json     = asdict(report_data),
            overall_health_score    = m.overall_health_score,
            risk_score              = m.risk_score,
            security_score          = m.security_score,
            performance_score       = m.performance_score,
            architecture_score      = m.architecture_score,
            maintainability_score   = m.maintainability_score,
            technical_debt_score    = m.technical_debt_score,
            complexity_score        = m.complexity_score,
            documentation_score     = m.documentation_score,
            testability_score       = m.testability_score,
            repository_snapshot_json = {
                "repository_id":   report_data.repository_id,
                "repository_name": report_data.repository_name,
                "generated_at":    report_data.generated_at,
            },
        )

    def mark_failed(self, report_id: str) -> None:
        self.repo.update_status(report_id, ReportStatusEnum.FAILED.value)

    # ── Retrieval ──────────────────────────────────────────────────────────

    def get_report(self, report_id: str) -> Optional[DBReport]:
        return self.repo.get_by_id(report_id)

    def get_report_by_review(self, review_id: str) -> Optional[DBReport]:
        return self.repo.get_by_review_id(review_id)

    def list_reports_by_repository(
        self,
        repository_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[DBReport]:
        return self.repo.list_by_repository(repository_id, skip, limit)

    def list_reports_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[DBReport]:
        return self.repo.list_by_user(user_id, skip, limit)

    def delete_report(self, report_id: str) -> bool:
        return self.repo.delete(report_id)

    # ── Export ─────────────────────────────────────────────────────────────

    def export_report(
        self,
        report_id: str,
        fmt: ExportFormatEnum,
    ) -> tuple[str | bytes, str]:
        """
        Returns (content, mime_type).
        Tracks which formats have been exported for this report.
        """
        db_report = self.repo.get_by_id(report_id)
        if not db_report or not db_report.report_content_json:
            raise ValueError(f"Report {report_id} not found or has no content.")

        report_data = _db_to_domain(db_report)

        if fmt == ExportFormatEnum.MARKDOWN:
            content   = self.exporter.to_markdown(report_data)
            mime_type = "text/markdown"
        elif fmt == ExportFormatEnum.HTML:
            content   = self.exporter.to_html(report_data)
            mime_type = "text/html"
        elif fmt == ExportFormatEnum.JSON:
            content   = self.exporter.to_json(report_data)
            mime_type = "application/json"
        elif fmt == ExportFormatEnum.SARIF:
            content   = self.exporter.to_sarif(report_data)
            mime_type = "application/sarif+json"
        elif fmt == ExportFormatEnum.PDF:
            content   = self.exporter.to_pdf(report_data)
            mime_type = "application/pdf"
        else:
            raise ValueError(f"Unsupported export format: {fmt}")

        self.repo.append_export_format(report_id, fmt.value)
        logger.info("report_exported", report_id=report_id, format=fmt.value)
        return content, mime_type

    # ── Side-by-side comparison ────────────────────────────────────────────

    def compare_reports(
        self,
        report_id_a: str,
        report_id_b: str,
    ) -> Dict[str, Any]:
        """
        Compare two historical reports and return score deltas and
        finding count changes.
        """
        a = self.repo.get_by_id(report_id_a)
        b = self.repo.get_by_id(report_id_b)

        if not a or not b:
            raise ValueError("One or both reports not found.")

        def _scores(r: DBReport) -> Dict[str, float]:
            return {
                "overall_health_score":  r.overall_health_score or 0.0,
                "risk_score":            r.risk_score or 0.0,
                "security_score":        r.security_score or 0.0,
                "performance_score":     r.performance_score or 0.0,
                "architecture_score":    r.architecture_score or 0.0,
                "maintainability_score": r.maintainability_score or 0.0,
                "technical_debt_score":  r.technical_debt_score or 0.0,
                "complexity_score":      r.complexity_score or 0.0,
                "documentation_score":   r.documentation_score or 0.0,
                "testability_score":     r.testability_score or 0.0,
            }

        def _counts(r: DBReport) -> Dict[str, int]:
            content = r.report_content_json or {}
            return {
                "code_review":     len(content.get("code_review_findings", [])),
                "security":        len(content.get("security_findings", [])),
                "performance":     len(content.get("performance_findings", [])),
                "refactoring":     len(content.get("refactoring_findings", [])),
                "architecture":    len(content.get("architecture_findings", [])),
                "action_items":    len(content.get("action_items", [])),
            }

        scores_a = _scores(a)
        scores_b = _scores(b)
        counts_a = _counts(a)
        counts_b = _counts(b)

        deltas = {k: round(scores_b[k] - scores_a[k], 2) for k in scores_a}
        count_deltas = {k: counts_b[k] - counts_a[k] for k in counts_a}

        return {
            "report_a": {"id": a.id, "created_at": str(a.created_at), "scores": scores_a, "finding_counts": counts_a},
            "report_b": {"id": b.id, "created_at": str(b.created_at), "scores": scores_b, "finding_counts": counts_b},
            "score_deltas": deltas,
            "finding_count_deltas": count_deltas,
            "improved_metrics":  [k for k, v in deltas.items() if v > 0],
            "degraded_metrics":  [k for k, v in deltas.items() if v < 0],
        }


# ── Utility ────────────────────────────────────────────────────────────────────

def _db_to_domain(db: DBReport) -> EngineeringReportData:
    """Reconstruct an EngineeringReportData from a persisted DBReport."""
    content = db.report_content_json or {}
    metrics_raw = content.get("metrics", {})
    if isinstance(metrics_raw, dict):
        metrics = EngineeringReportMetrics(**{
            k: v for k, v in metrics_raw.items()
            if k in EngineeringReportMetrics.__dataclass_fields__
        })
    else:
        metrics = EngineeringReportMetrics()

    # Re-hydrate action_items as ActionItem instances
    raw_action_items = content.get("action_items", [])
    action_items: list[ActionItem] = []
    for item in raw_action_items:
        if isinstance(item, dict):
            action_items.append(ActionItem(
                priority               = item.get("priority", "medium"),
                title                  = item.get("title", ""),
                description            = item.get("description", ""),
                category               = item.get("category", ""),
                estimated_effort_hours = float(item.get("estimated_effort_hours", 0.0)),
                agent_source           = item.get("agent_source", ""),
            ))
        elif isinstance(item, ActionItem):
            action_items.append(item)

    return EngineeringReportData(
        report_id            = content.get("report_id", db.id),
        review_id            = content.get("review_id", db.review_id or ""),
        repository_id        = content.get("repository_id", db.repository_id),
        repository_name      = content.get("repository_name", ""),
        generated_at         = content.get("generated_at", str(db.created_at)),
        report_version       = content.get("report_version", db.version),
        executive_summary    = content.get("executive_summary", ""),
        repository_overview  = content.get("repository_overview", {}),
        code_review_findings     = content.get("code_review_findings", []),
        code_review_summary      = content.get("code_review_summary", ""),
        security_findings        = content.get("security_findings", []),
        security_summary         = content.get("security_summary", ""),
        performance_findings     = content.get("performance_findings", []),
        performance_recommendations = content.get("performance_recommendations", []),
        performance_summary      = content.get("performance_summary", ""),
        refactoring_findings     = content.get("refactoring_findings", []),
        refactoring_summary      = content.get("refactoring_summary", ""),
        architecture_findings    = content.get("architecture_findings", []),
        dependency_analysis      = content.get("dependency_analysis", {}),
        architecture_summary     = content.get("architecture_summary", ""),
        metrics                  = metrics,
        total_technical_debt_hours = content.get("total_technical_debt_hours", 0.0),
        tech_debt_breakdown      = content.get("tech_debt_breakdown", {}),
        tech_debt_summary        = content.get("tech_debt_summary", ""),
        complexity_hotspots      = content.get("complexity_hotspots", []),
        complexity_summary       = content.get("complexity_summary", ""),
        maintainability_issues   = content.get("maintainability_issues", []),
        maintainability_summary  = content.get("maintainability_summary", ""),
        hotspot_files            = content.get("hotspot_files", []),
        risk_level               = content.get("risk_level", "medium"),
        risk_factors             = content.get("risk_factors", []),
        risk_summary             = content.get("risk_summary", ""),
        action_items             = action_items,   # kept as list[dict]
        future_improvements      = content.get("future_improvements", []),
        future_improvements_summary = content.get("future_improvements_summary", ""),
    )
