from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.domain.entities.workspace import Workspace, WorkspaceCreate, WorkspaceUpdate
from src.application.services.workspace_service import WorkspaceService
from src.infrastructure.repositories.workspace_repository import WorkspaceRepository
from src.interfaces.api.dependencies import get_current_user

# We need a dependency to get the DB session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.config import settings

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_workspace_service(db: Session = Depends(get_db)) -> WorkspaceService:
    repo = WorkspaceRepository(db)
    return WorkspaceService(repo)

@router.post("", response_model=Workspace, status_code=status.HTTP_201_CREATED)
def create_workspace(
    data: WorkspaceCreate,
    current_user: dict = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service)
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    return service.create_workspace(user_id, data)

@router.get("", response_model=List[Workspace])
def list_workspaces(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service)
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    return service.list_workspaces(user_id, skip, limit)

@router.get("/{workspace_id}", response_model=Workspace)
def get_workspace(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service)
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
        
    workspace = service.get_workspace(user_id, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.put("/{workspace_id}", response_model=Workspace)
def update_workspace(
    workspace_id: str,
    data: WorkspaceUpdate,
    current_user: dict = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service)
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
        
    workspace = service.update_workspace(user_id, workspace_id, data)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or unauthorized")
    return workspace

@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service)
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
        
    success = service.delete_workspace(user_id, workspace_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found or unauthorized")
