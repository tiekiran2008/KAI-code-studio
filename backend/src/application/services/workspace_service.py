from typing import List, Optional
from src.domain.entities.workspace import Workspace, WorkspaceCreate, WorkspaceUpdate
from src.infrastructure.repositories.workspace_repository import WorkspaceRepository

class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    def _to_entity(self, db_workspace) -> Workspace:
        # Compute repo count based on relationship
        repo_count = len(db_workspace.repositories) if db_workspace.repositories else 0
        return Workspace(
            id=db_workspace.id,
            user_id=db_workspace.user_id,
            name=db_workspace.name,
            description=db_workspace.description,
            default_ai_model=db_workspace.default_ai_model,
            default_repo_id=db_workspace.default_repo_id,
            vector_db_config=db_workspace.vector_db_config,
            tool_config=db_workspace.tool_config,
            created_at=db_workspace.created_at,
            updated_at=db_workspace.updated_at,
            repo_count=repo_count
        )

    def create_workspace(self, user_id: str, data: WorkspaceCreate) -> Workspace:
        data_dict = data.model_dump(exclude_unset=True)
        # Ensure an empty-string default_repo_id never reaches the DB FK column
        if data_dict.get("default_repo_id") == "":
            data_dict["default_repo_id"] = None
        db_workspace = self.repository.create(user_id, data_dict)
        return self._to_entity(db_workspace)

    def get_workspace(self, user_id: str, workspace_id: str) -> Optional[Workspace]:
        db_workspace = self.repository.get_by_id(workspace_id)
        if not db_workspace or db_workspace.user_id != user_id:
            return None
        return self._to_entity(db_workspace)

    def list_workspaces(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Workspace]:
        db_workspaces = self.repository.get_all_by_user(user_id, skip, limit)
        return [self._to_entity(w) for w in db_workspaces]

    def update_workspace(self, user_id: str, workspace_id: str, data: WorkspaceUpdate) -> Optional[Workspace]:
        # Validate ownership
        db_workspace = self.repository.get_by_id(workspace_id)
        if not db_workspace or db_workspace.user_id != user_id:
            return None
            
        update_data = data.model_dump(exclude_unset=True)
        updated_db_workspace = self.repository.update(workspace_id, update_data)
        if not updated_db_workspace:
            return None
            
        return self._to_entity(updated_db_workspace)

    def delete_workspace(self, user_id: str, workspace_id: str) -> bool:
        db_workspace = self.repository.get_by_id(workspace_id)
        if not db_workspace or db_workspace.user_id != user_id:
            return False
            
        return self.repository.delete(workspace_id)
