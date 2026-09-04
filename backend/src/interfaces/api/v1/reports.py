"""
Engineering Reports API — v1
==============================
Endpoints:
  POST   /api/v1/reports/generate          Generate a report from an existing review
  GET    /api/v1/reports                   List reports for the current user
  GET    /api/v1/reports/{report_id}       Get a single report
  DELETE /api/v1/reports/{report_id}       Delete a report
  GET    /api/v1/reports/{report_id}/export?format=markdown|html|json|sarif|pdf
  POST   /api/v1/reports/compare           Compare two reports side-by-side
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.interfaces.api.dependencies import get_db_session as get_db, get_current_user
from src.domain.entities.user import User
from src.domain.entities.report_entity import (
    ExportFormatEnum,
    ReportStatusEnum,
    EngineeringReportData,
    EngineeringReportMetrics,
    ActionItem,
)
from src.application.services.report_service import ReportService
from src.infrastructure.repositories.report_repository import ReportRepository
from src.infrastructure.persistence.report_models import DBReport
from src.core.logger import logger


# ── Dependency ────────────────────────────────────────────────────────────────

def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(ReportRepository(db))


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
    repository_id: str
    review_id: Optional[str] = None
    title: str = "Engineering Report"


class CompareReportsRequest(BaseModel):
    report_id_a: str
    report_id_b: str


def _report_to_dict(r: DBReport) -> dict:
    """Serialize a DBReport ORM object to a JSON-safe dict."""
    return {
        "id":                    r.id,
        "repository_id":         r.repository_id,
        "review_id":             r.review_id,
        "user_id":               r.user_id,
        "title":                 r.title,
        "version":               r.version,
        "status":                r.status,
        "overall_health_score":  r.overall_health_score,
        "risk_score":            r.risk_score,
        "security_score":        r.security_score,
        "performance_score":     r.performance_score,
        "architecture_score":    r.architecture_score,
        "maintainability_score": r.maintainability_score,
        "technical_debt_score":  r.technical_debt_score,
        "complexity_score":      r.complexity_score,
        "documentation_score":   r.documentation_score,
        "testability_score":     r.testability_score,
        "repository_snapshot":   r.repository_snapshot_json or {},
        "export_formats":        r.export_formats_json or [],
        "report_content":        r.report_content_json or {},
        "created_at":            str(r.created_at) if r.created_at else None,
        "updated_at":            str(r.updated_at) if r.updated_at else None,
    }


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/reports", tags=["reports"])

# ── MIME types per format ─────────────────────────────────────────────────────
_MIME = {
    ExportFormatEnum.MARKDOWN: "text/markdown",
    ExportFormatEnum.HTML:     "text/html",
    ExportFormatEnum.JSON:     "application/json",
    ExportFormatEnum.SARIF:    "application/sarif+json",
    ExportFormatEnum.PDF:      "application/pdf",
}
_EXTENSION = {
    ExportFormatEnum.MARKDOWN: "md",
    ExportFormatEnum.HTML:     "html",
    ExportFormatEnum.JSON:     "json",
    ExportFormatEnum.SARIF:    "sarif",
    ExportFormatEnum.PDF:      "pdf",
}


@router.post("/generate")
async def generate_report(
    request: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    """
    Generate an engineering report for a repository / completed review.
    The agent_outputs from the review workflow are re-synthesised into a
    structured report and persisted as a new DBReport record.
    """
    import uuid
    from dataclasses import asdict
    from datetime import datetime, timezone

    # 1. Create a pending record
    db_report = service.create_report_record(
        user_id       = current_user.id,
        repository_id = request.repository_id,
        review_id     = request.review_id,
        title         = request.title,
    )

    try:
        # 2. Build a stub EngineeringReportData from the review DB record if available
        #    In a full integration, the ReviewCodeUseCase would pass agent_outputs
        #    to the ReportGeneratorAgent via the LangGraph workflow.
        #    Here we provide a synthesised report from any existing code review data.

        from src.infrastructure.repositories.code_review_repository import CodeReviewRepository
        from sqlalchemy.orm import Session

        # Pull existing analysis data from the linked review if provided
        report_content: dict = {}
        if request.review_id:
            # Build a minimal EngineeringReportData from the persisted review
            from src.infrastructure.persistence.code_review_models import DBCodeReview
            db_session: Session = service.repo.db
            cr: DBCodeReview = db_session.query(DBCodeReview).filter(
                DBCodeReview.id == request.review_id
            ).first()

            if cr:
                from src.domain.entities.report_entity import EngineeringReportMetrics
                metrics = EngineeringReportMetrics(
                    overall_health_score   = cr.overall_health_score or 0.0,
                    risk_score             = max(0.0, 100.0 - (cr.overall_health_score or 50.0)),
                    security_score         = 0.0,
                    performance_score      = cr.performance_score or 0.0,
                    architecture_score     = cr.architecture_score or 0.0,
                    maintainability_score  = cr.maintainability_score or 0.0,
                    technical_debt_score   = cr.technical_debt_score or 0.0,
                    complexity_score       = cr.complexity_score or 0.0,
                    documentation_score    = cr.documentation_score or 0.0,
                    testability_score      = cr.testability_score or 0.0,
                )

                from src.domain.entities.report_entity import EngineeringReportData
                rd = EngineeringReportData(
                    report_id           = db_report.id,
                    review_id           = request.review_id,
                    repository_id       = request.repository_id,
                    repository_name     = request.repository_id,
                    generated_at        = datetime.now(timezone.utc).isoformat(),
                    report_version      = "1.0",
                    executive_summary   = (
                        f"Engineering report generated from review {request.review_id}. "
                        f"Overall health score: {cr.overall_health_score or 0:.1f}/100. "
                        f"Identified {len(cr.findings_json or [])} code quality issues, "
                        f"{len(cr.performance_findings_json or [])} performance findings, "
                        f"{len(cr.refactoring_findings_json or [])} refactoring opportunities, "
                        f"and {len(cr.architecture_findings_json or [])} architecture issues."
                    ),
                    code_review_findings   = cr.findings_json or [],
                    security_findings      = [],
                    performance_findings   = cr.performance_findings_json or [],
                    performance_recommendations = cr.performance_recommendations_json or [],
                    refactoring_findings   = cr.refactoring_findings_json or [],
                    architecture_findings  = cr.architecture_findings_json or [],
                    dependency_analysis    = cr.dependency_analysis_json or {},
                    metrics                = metrics,
                    total_technical_debt_hours = cr.estimated_refactoring_effort or 0.0,
                    hotspot_files          = (cr.dependency_analysis_json or {}).get("hotspot_files", []),
                    risk_level             = "high" if (cr.overall_health_score or 100) < 60 else "medium",
                )
                report_content = asdict(rd)

        # 3. Persist
        if report_content:
            updated = service.repo.update_content(
                db_report.id,
                status              = ReportStatusEnum.COMPLETED.value,
                report_content_json = report_content,
                overall_health_score    = report_content.get("metrics", {}).get("overall_health_score", 0.0),
                risk_score              = report_content.get("metrics", {}).get("risk_score", 0.0),
                security_score          = report_content.get("metrics", {}).get("security_score", 0.0),
                performance_score       = report_content.get("metrics", {}).get("performance_score", 0.0),
                architecture_score      = report_content.get("metrics", {}).get("architecture_score", 0.0),
                maintainability_score   = report_content.get("metrics", {}).get("maintainability_score", 0.0),
                technical_debt_score    = report_content.get("metrics", {}).get("technical_debt_score", 0.0),
                complexity_score        = report_content.get("metrics", {}).get("complexity_score", 0.0),
                documentation_score     = report_content.get("metrics", {}).get("documentation_score", 0.0),
                testability_score       = report_content.get("metrics", {}).get("testability_score", 0.0),
            )
            return _report_to_dict(updated)

        # Fallback: return pending record
        return _report_to_dict(db_report)

    except Exception as e:
        service.mark_failed(db_report.id)
        logger.error("report_generate_failed", error=str(e), report_id=db_report.id)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("")
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    """List all engineering reports for the current user."""
    reports = service.list_reports_by_user(current_user.id, skip=skip, limit=limit)
    return [_report_to_dict(r) for r in reports]


@router.get("/{report_id}")
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    """Get a single engineering report by ID."""
    report = service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return _report_to_dict(report)


@router.delete("/{report_id}", status_code=204)
def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    """Delete an engineering report."""
    deleted = service.delete_report(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found.")


@router.get("/{report_id}/export")
def export_report(
    report_id: str,
    format: ExportFormatEnum = Query(ExportFormatEnum.MARKDOWN, description="Export format"),
    current_user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    """
    Export a report in the specified format.
    Supported: markdown, html, json, sarif, pdf
    """
    try:
        content, mime_type = service.export_report(report_id, format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("report_export_failed", error=str(e), report_id=report_id)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    ext = _EXTENSION.get(format, "txt")
    filename = f"engineering_report_{report_id[:8]}.{ext}"

    if isinstance(content, str):
        raw = content.encode("utf-8")
    else:
        raw = content

    return Response(
        content     = raw,
        media_type  = mime_type,
        headers     = {"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/compare")
def compare_reports(
    request: CompareReportsRequest,
    current_user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    """
    Side-by-side comparison of two historical engineering reports.
    Returns score deltas and finding count changes.
    """
    try:
        return service.compare_reports(request.report_id_a, request.report_id_b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("report_compare_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")
