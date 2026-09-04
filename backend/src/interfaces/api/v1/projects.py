from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.domain.entities.project import Project, ProjectCreate, ProjectUpdate, ProjectDashboard
from src.infrastructure.repositories.project_repository import ProjectRepository
from src.infrastructure.repositories.repository_repository import RepositoryRepository
from src.application.services.project_service import ProjectService
from src.application.services.repository_service import RepositoryService
from src.interfaces.api.dependencies import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])

engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    p_repo = ProjectRepository(db)
    r_repo = RepositoryRepository(db)
    r_service = RepositoryService(r_repo)
    return ProjectService(p_repo, r_service)

@router.get("", response_model=List[Project])
def list_projects(
    workspace_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    return service.list_projects(user_id, workspace_id, skip, limit)

@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    return service.create_project(user_id, data)

@router.get("/{project_id}", response_model=Project)
def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    project = service.get_project(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=Project)
def update_project(
    project_id: str,
    data: ProjectUpdate,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    project = service.update_project(user_id, project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")
    return project

@router.post("/{project_id}/archive", response_model=Project)
def archive_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    project = service.archive_project(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    success = service.delete_project(user_id, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")

@router.post("/{project_id}/repositories/{repo_id}", response_model=Project)
def link_repository(
    project_id: str,
    repo_id: str,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    project = service.link_repository(user_id, project_id, repo_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project or repository not found or unauthorized")
    return project

@router.delete("/{project_id}/repositories/{repo_id}", response_model=Project)
def unlink_repository(
    project_id: str,
    repo_id: str,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    project = service.unlink_repository(user_id, project_id, repo_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized")
    return project

@router.get("/{project_id}/dashboard", response_model=ProjectDashboard)
def get_project_dashboard(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    dashboard = service.get_dashboard(user_id, project_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Project not found")
    return dashboard
