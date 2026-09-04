from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks

from src.domain.entities.repository import (
    Repository,
    RepositoryCreate,
    RepositoryUpdate,
    RepositorySwitchBranch,
    RepositoryHealthCheck,
    RepositoryListParams,
    RepositoryProvider,
    IndexingStatus,
    RepositoryIndexStatus,
)
from src.application.services.repository_service import RepositoryService
from src.application.services.repository_ingestion_service import RepositoryIngestionService
from src.interfaces.api.dependencies import (
    get_current_user,
    get_repository_service,
    get_repository_ingestion_service,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("", response_model=List[Repository])
def list_repositories(
    workspace_id: Optional[str] = Query(None),
    provider: Optional[RepositoryProvider] = Query(None),
    indexing_status: Optional[IndexingStatus] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    sort_by: str = Query("updated_at"),
    sort_dir: str = Query("desc"),
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")

    params = RepositoryListParams(
        workspace_id=workspace_id,
        provider=provider,
        indexing_status=indexing_status,
        search=search,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return service.list_repositories(user_id, params)


@router.post("/import", response_model=Repository, status_code=status.HTTP_201_CREATED)
def import_repository(
    data: RepositoryCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
    ingestion_service: RepositoryIngestionService = Depends(get_repository_ingestion_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    try:
        repo = service.import_repository(user_id, data)
        # Launch background indexing task
        background_tasks.add_task(ingestion_service.ingest_repository, repo.id, user_id)
        return repo
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{repo_id}/index-status", response_model=RepositoryIndexStatus)
def get_index_status(
    repo_id: str,
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
    ingestion_service: RepositoryIngestionService = Depends(get_repository_ingestion_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    repo = service.get_repository(user_id, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    prog = ingestion_service.get_progress(repo_id)
    return RepositoryIndexStatus(
        repository_id=repo_id,
        status=prog.status,
        stage=prog.stage,
        progress=prog.progress,
        files_discovered=prog.files_discovered,
        files_processed=prog.files_processed,
        chunks_created=prog.chunks_created or repo.chunks_count,
        error=prog.error,
        started_at=prog.started_at,
        completed_at=prog.completed_at,
    )


@router.post("/{repo_id}/reindex", response_model=RepositoryIndexStatus)
def reindex_repository(
    repo_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
    ingestion_service: RepositoryIngestionService = Depends(get_repository_ingestion_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    repo = service.get_repository(user_id, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Queue re-indexing in background
    background_tasks.add_task(ingestion_service.ingest_repository, repo_id, user_id)
    return RepositoryIndexStatus(
        repository_id=repo_id,
        status="indexing",
        stage="cloning",
        progress=5.0,
        files_discovered=0,
        files_processed=0,
        chunks_created=0,
    )


@router.get("/{repo_id}", response_model=Repository)
def get_repository(
    repo_id: str,
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    repo = service.get_repository(user_id, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.put("/{repo_id}", response_model=Repository)
def update_repository(
    repo_id: str,
    data: RepositoryUpdate,
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    repo = service.update_repository(user_id, repo_id, data)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found or unauthorized")
    return repo


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(
    repo_id: str,
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    success = service.delete_repository(user_id, repo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Repository not found or unauthorized")


@router.post("/{repo_id}/refresh", response_model=Repository)
def refresh_repository(
    repo_id: str,
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    repo = service.refresh_repository(user_id, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found or unauthorized")
    return repo


@router.get("/{repo_id}/health", response_model=RepositoryHealthCheck)
def repository_health_check(
    repo_id: str,
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    return service.health_check(user_id, repo_id)


@router.get("/{repo_id}/branches", response_model=List[str])
def list_branches(
    repo_id: str,
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    repo = service.get_repository(user_id, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo.branches


@router.patch("/{repo_id}/branch", response_model=Repository)
def switch_branch(
    repo_id: str,
    data: RepositorySwitchBranch,
    current_user: dict = Depends(get_current_user),
    service: RepositoryService = Depends(get_repository_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    repo = service.switch_branch(user_id, repo_id, data.branch)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found or unauthorized")
    return repo
