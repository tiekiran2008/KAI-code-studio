"""
Engineering Report ORM Persistence Model
=========================================
SQLAlchemy model that stores generated engineering reports.
Each DBReport stores the full JSON payload, aggregated metric scores,
repository snapshot metadata, and export history.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, func
from src.infrastructure.persistence.base import Base


class DBReport(Base):
    __tablename__ = "engineering_reports"

    id                      = Column(String, primary_key=True)
    repository_id           = Column(String, nullable=False, index=True)
    review_id               = Column(String, nullable=True, index=True)   # linked CodeReview
    user_id                 = Column(String, nullable=False, index=True)
    title                   = Column(String, nullable=False, default="Engineering Report")
    version                 = Column(String, nullable=False, default="1.0")
    status                  = Column(String, nullable=False, default="pending")

    # ── Full report JSON payload ──────────────────────────────────────────
    report_content_json     = Column(JSON, default=dict)

    # ── Aggregated metric scores (0.0 – 100.0) ───────────────────────────
    overall_health_score    = Column(Float, default=0.0)
    risk_score              = Column(Float, default=0.0)
    security_score          = Column(Float, default=0.0)
    performance_score       = Column(Float, default=0.0)
    architecture_score      = Column(Float, default=0.0)
    maintainability_score   = Column(Float, default=0.0)
    technical_debt_score    = Column(Float, default=0.0)
    complexity_score        = Column(Float, default=0.0)
    documentation_score     = Column(Float, default=0.0)
    testability_score       = Column(Float, default=0.0)

    # ── Repository snapshot metadata ──────────────────────────────────────
    repository_snapshot_json = Column(JSON, default=dict)

    # ── Export format tracking ────────────────────────────────────────────
    export_formats_json     = Column(JSON, default=list)   # list of exported format strings

    # ── Timestamps ───────────────────────────────────────────────────────
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())
