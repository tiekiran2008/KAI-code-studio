"""
Repository Repository (Data Access Layer)
==========================================
Handles all SQLAlchemy CRUD and query operations for DBRepository.
Follows the same pattern as workspace_repository.py.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import DBRepository
from src.domain.entities.repository import RepositoryListParams


class RepositoryRepository:
    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def create(self, user_id: str, data: dict) -> DBRepository:
        repo = DBRepository(
            id=str(uuid.uuid4()),
            user_id=user_id,
            **data,
        )
        self.session.add(repo)
        self.session.commit()
        self.session.refresh(repo)
        return repo

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def get_by_id(self, repo_id: str) -> Optional[DBRepository]:
        return self.session.query(DBRepository).filter(DBRepository.id == repo_id).first()

    def get_by_user_and_url(self, user_id: str, url: str) -> Optional[DBRepository]:
        """Used for duplicate prevention."""
        return (
            self.session.query(DBRepository)
            .filter(DBRepository.user_id == user_id, DBRepository.url == url)
            .first()
        )

    def list_by_user(self, user_id: str, params: RepositoryListParams) -> List[DBRepository]:
        q = self.session.query(DBRepository).filter(DBRepository.user_id == user_id)

        if params.workspace_id:
            q = q.filter(DBRepository.workspace_id == params.workspace_id)
        if params.provider:
            q = q.filter(DBRepository.provider == params.provider.value)
        if params.indexing_status:
            q = q.filter(DBRepository.indexing_status == params.indexing_status.value)
        if params.search:
            term = f"%{params.search}%"
            q = q.filter(
                or_(
                    DBRepository.name.ilike(term),
                    DBRepository.description.ilike(term),
                    DBRepository.owner.ilike(term),
                    DBRepository.url.ilike(term),
                )
            )

        # Sorting
        sort_col = getattr(DBRepository, params.sort_by, DBRepository.updated_at)
        if params.sort_dir == "asc":
            q = q.order_by(sort_col.asc())
        else:
            q = q.order_by(sort_col.desc())

        return q.offset(params.skip).limit(params.limit).all()

    def count_by_user(self, user_id: str) -> int:
        return self.session.query(DBRepository).filter(DBRepository.user_id == user_id).count()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, repo_id: str, data: dict) -> Optional[DBRepository]:
        repo = self.get_by_id(repo_id)
        if not repo:
            return None
        for key, value in data.items():
            if hasattr(repo, key):
                setattr(repo, key, value)
        # Manually bump updated_at since onupdate doesn't fire on attribute set
        repo.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(repo)
        return repo

    def set_indexing_status(self, repo_id: str, status: str, chunks_count: int = 0) -> Optional[DBRepository]:
        repo = self.get_by_id(repo_id)
        if not repo:
            return None
        repo.indexing_status = status
        if status == "indexed":
            repo.last_indexed_at = datetime.now(timezone.utc)
            repo.chunks_count = chunks_count
        repo.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(repo)
        return repo

    def switch_branch(self, repo_id: str, branch: str) -> Optional[DBRepository]:
        repo = self.get_by_id(repo_id)
        if not repo:
            return None
        repo.current_branch = branch
        # Add to branches list if not already present
        branches = list(repo.branches_json or [])
        if branch not in branches:
            branches.append(branch)
            repo.branches_json = branches
        repo.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(repo)
        return repo

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    def delete(self, repo_id: str) -> bool:
        repo = self.get_by_id(repo_id)
        if not repo:
            return False
        self.session.delete(repo)
        self.session.commit()
        return True
