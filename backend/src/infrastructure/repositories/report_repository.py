"""
Report Repository
==================
Infrastructure repository for CRUD operations on DBReport ORM models.
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from src.infrastructure.persistence.report_models import DBReport


class ReportRepository:
    """Data-access layer for engineering reports."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────────────

    def create(self, report: DBReport) -> DBReport:
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    # ── Read ──────────────────────────────────────────────────────────────

    def get_by_id(self, report_id: str) -> Optional[DBReport]:
        return self.db.query(DBReport).filter(DBReport.id == report_id).first()

    def get_by_review_id(self, review_id: str) -> Optional[DBReport]:
        return self.db.query(DBReport).filter(DBReport.review_id == review_id).first()

    def list_by_repository(
        self,
        repository_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[DBReport]:
        return (
            self.db.query(DBReport)
            .filter(DBReport.repository_id == repository_id)
            .order_by(DBReport.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[DBReport]:
        return (
            self.db.query(DBReport)
            .filter(DBReport.user_id == user_id)
            .order_by(DBReport.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_all(self, skip: int = 0, limit: int = 100) -> List[DBReport]:
        return (
            self.db.query(DBReport)
            .order_by(DBReport.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ── Update ────────────────────────────────────────────────────────────

    def update_status(self, report_id: str, status: str) -> Optional[DBReport]:
        report = self.get_by_id(report_id)
        if report:
            report.status = status
            self.db.commit()
            self.db.refresh(report)
        return report

    def update_content(self, report_id: str, **kwargs) -> Optional[DBReport]:
        report = self.get_by_id(report_id)
        if report:
            for key, value in kwargs.items():
                if hasattr(report, key):
                    setattr(report, key, value)
            self.db.commit()
            self.db.refresh(report)
        return report

    def append_export_format(self, report_id: str, fmt: str) -> Optional[DBReport]:
        report = self.get_by_id(report_id)
        if report:
            formats = list(report.export_formats_json or [])
            if fmt not in formats:
                formats.append(fmt)
                report.export_formats_json = formats
                self.db.commit()
                self.db.refresh(report)
        return report

    # ── Delete ────────────────────────────────────────────────────────────

    def delete(self, report_id: str) -> bool:
        report = self.get_by_id(report_id)
        if report:
            self.db.delete(report)
            self.db.commit()
            return True
        return False
