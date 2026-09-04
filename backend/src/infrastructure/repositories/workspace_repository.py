import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from src.infrastructure.persistence.workspace_models import DBWorkspace

class WorkspaceRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: str, data: dict) -> DBWorkspace:
        workspace_id = str(uuid.uuid4())
        db_workspace = DBWorkspace(
            id=workspace_id,
            user_id=user_id,
            **data
        )
        self.session.add(db_workspace)
        self.session.commit()
        self.session.refresh(db_workspace)
        return db_workspace

    def get_by_id(self, workspace_id: str) -> Optional[DBWorkspace]:
        return self.session.query(DBWorkspace).filter(DBWorkspace.id == workspace_id).first()

    def get_all_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[DBWorkspace]:
        return self.session.query(DBWorkspace).filter(DBWorkspace.user_id == user_id).offset(skip).limit(limit).all()

    def update(self, workspace_id: str, data: dict) -> Optional[DBWorkspace]:
        db_workspace = self.get_by_id(workspace_id)
        if not db_workspace:
            return None
        
        for key, value in data.items():
            if hasattr(db_workspace, key):
                setattr(db_workspace, key, value)
                
        self.session.commit()
        self.session.refresh(db_workspace)
        return db_workspace

    def delete(self, workspace_id: str) -> bool:
        db_workspace = self.get_by_id(workspace_id)
        if not db_workspace:
            return False
            
        self.session.delete(db_workspace)
        self.session.commit()
        return True
