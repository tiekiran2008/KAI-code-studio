import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from src.infrastructure.persistence.project_models import DBProject, DBProjectRepository
from src.infrastructure.persistence.models import DBRepository

class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: str, data: dict, repository_ids: Optional[List[str]] = None) -> DBProject:
        project_id = str(uuid.uuid4())
        project = DBProject(
            id=project_id,
            user_id=user_id,
            **data
        )
        self.session.add(project)
        self.session.flush()

        if repository_ids:
            for repo_id in repository_ids:
                link = DBProjectRepository(project_id=project_id, repository_id=repo_id)
                self.session.add(link)

        self.session.commit()
        self.session.refresh(project)
        return project

    def get_by_id(self, project_id: str) -> Optional[DBProject]:
        return self.session.query(DBProject).filter(DBProject.id == project_id).first()

    def list_by_user(self, user_id: str, workspace_id: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[DBProject]:
        query = self.session.query(DBProject).filter(DBProject.user_id == user_id)
        if workspace_id:
            query = query.filter(DBProject.workspace_id == workspace_id)
        return query.order_by(DBProject.updated_at.desc()).offset(skip).limit(limit).all()

    def update(self, project_id: str, data: dict) -> Optional[DBProject]:
        project = self.get_by_id(project_id)
        if not project:
            return None
        for key, value in data.items():
            if hasattr(project, key) and value is not None:
                setattr(project, key, value)
        self.session.commit()
        self.session.refresh(project)
        return project

    def link_repository(self, project_id: str, repo_id: str) -> bool:
        existing = (
            self.session.query(DBProjectRepository)
            .filter_by(project_id=project_id, repository_id=repo_id)
            .first()
        )
        if existing:
            return True
        link = DBProjectRepository(project_id=project_id, repository_id=repo_id)
        self.session.add(link)
        self.session.commit()
        return True

    def unlink_repository(self, project_id: str, repo_id: str) -> bool:
        link = (
            self.session.query(DBProjectRepository)
            .filter_by(project_id=project_id, repository_id=repo_id)
            .first()
        )
        if not link:
            return False
        self.session.delete(link)
        self.session.commit()
        return True

    def delete(self, project_id: str) -> bool:
        project = self.get_by_id(project_id)
        if not project:
            return False
        self.session.delete(project)
        self.session.commit()
        return True
