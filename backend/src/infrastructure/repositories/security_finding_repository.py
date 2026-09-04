from typing import List, Optional
from sqlalchemy.orm import Session
from src.infrastructure.persistence.security_finding_models import DBSecurityFinding
from src.domain.entities.security_finding import SecurityFinding

class SecurityFindingRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def create(self, review_id: str, finding: SecurityFinding) -> DBSecurityFinding:
        db_finding = DBSecurityFinding(
            review_id=review_id,
            vulnerability=finding.vulnerability,
            severity=finding.severity.value if hasattr(finding.severity, 'value') else finding.severity,
            cwe_id=finding.cwe_id,
            owasp_category=finding.owasp_category,
            file_path=finding.file_path,
            line_number=finding.line_number,
            explanation=finding.explanation,
            attack_scenario=finding.attack_scenario,
            suggested_fix=finding.suggested_fix,
            confidence=finding.confidence,
        )
        self.db.add(db_finding)
        self.db.commit()
        self.db.refresh(db_finding)
        return db_finding

    def list_by_review(self, review_id: str, skip: int = 0, limit: int = 100) -> List[DBSecurityFinding]:
        return (
            self.db.query(DBSecurityFinding)
            .filter(DBSecurityFinding.review_id == review_id)
            .order_by(DBSecurityFinding.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def delete_by_review(self, review_id: str) -> int:
        deleted = self.db.query(DBSecurityFinding).filter(DBSecurityFinding.review_id == review_id).delete()
        self.db.commit()
        return deleted
