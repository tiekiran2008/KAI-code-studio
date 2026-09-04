from typing import List, Optional
from sqlalchemy.orm import Session
from src.infrastructure.persistence.code_review_models import DBCodeReview
from src.domain.entities.code_review import CodeReview, CodeReviewCreate, ReviewStatusEnum

class CodeReviewRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def create(self, review_data: CodeReviewCreate, user_id: str, review_id: str) -> DBCodeReview:
        db_review = DBCodeReview(
            id=review_id,
            repository_id=review_data.repository_id,
            user_id=user_id,
            status=ReviewStatusEnum.PENDING.value,
            progress_percent=0,
            current_stage="queued",
            progress_message="Review request queued",
            findings_json=[],

            confidence_score=1.0,
            duration_ms=None
        )
        self.db.add(db_review)
        self.db.commit()
        self.db.refresh(db_review)
        return db_review

    def get_by_id(self, review_id: str, user_id: Optional[str] = None) -> Optional[DBCodeReview]:
        query = self.db.query(DBCodeReview).filter(DBCodeReview.id == review_id)
        if user_id is not None:
            query = query.filter(DBCodeReview.user_id == user_id)
        return query.first()

    def get_by_repository(self, repository_id: str, user_id: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[DBCodeReview]:
        query = self.db.query(DBCodeReview).filter(DBCodeReview.repository_id == repository_id)
        if user_id is not None:
            query = query.filter(DBCodeReview.user_id == user_id)
        return (
            query.order_by(DBCodeReview.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_by_user(
        self,
        user_id: str,
        repository_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[DBCodeReview]:
        query = self.db.query(DBCodeReview).filter(DBCodeReview.user_id == user_id)
        if repository_id:
            query = query.filter(DBCodeReview.repository_id == repository_id)
        if status:
            query = query.filter(DBCodeReview.status == status)
        return (
            query.order_by(DBCodeReview.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(self, db_review: DBCodeReview) -> DBCodeReview:
        self.db.commit()
        self.db.refresh(db_review)
        return db_review

    def delete(self, review_id: str, user_id: Optional[str] = None) -> bool:
        review = self.get_by_id(review_id, user_id=user_id)
        if review:
            self.db.delete(review)
            self.db.commit()
            return True
        return False
