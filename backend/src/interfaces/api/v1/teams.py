from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.domain.entities.team import (
    Team, TeamCreate, TeamUpdate, TeamMember, RoleEnum, MemberRoleUpdate,
    TransferOwnership, AuditLog, PermissionMatrixRow
)
from src.application.services.team_service import TeamService
from src.application.services.permission_service import PermissionService
from src.interfaces.api.dependencies import get_current_user

router = APIRouter(prefix="/teams", tags=["teams"])

engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_team_service(db: Session = Depends(get_db)) -> TeamService:
    return TeamService(db)

@router.get("", response_model=List[Team])
def list_user_teams(
    current_user: dict = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return service.list_user_teams(user_id)

@router.post("", response_model=Team, status_code=status.HTTP_201_CREATED)
def create_team(
    data: TeamCreate,
    current_user: dict = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return service.create_team(user_id, data)

@router.get("/{team_id}", response_model=Team)
def get_team(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    team = service.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@router.put("/{team_id}", response_model=Team)
def update_team(
    team_id: str,
    data: TeamUpdate,
    current_user: dict = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    updated = service.update_team(user_id, team_id, data)
    if not updated:
        raise HTTPException(status_code=403, detail="Unauthorized to update team")
    return updated

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    success = service.delete_team(user_id, team_id)
    if not success:
        raise HTTPException(status_code=403, detail="Only the team Owner can delete the team")

@router.post("/{team_id}/transfer-ownership", response_model=Team)
def transfer_ownership(
    team_id: str,
    data: TransferOwnership,
    current_user: dict = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    updated = service.transfer_ownership(user_id, team_id, data.new_owner_user_id)
    if not updated:
        raise HTTPException(status_code=403, detail="Unauthorized or target user is not a member")
    return updated

@router.patch("/{team_id}/members/{target_user_id}/role", response_model=TeamMember)
def change_member_role(
    team_id: str,
    target_user_id: str,
    data: MemberRoleUpdate,
    current_user: dict = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        updated = service.change_member_role(user_id, team_id, target_user_id, data.role)
        if not updated:
            raise HTTPException(status_code=404, detail="Member or team not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.delete("/{team_id}/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    team_id: str,
    target_user_id: str,
    current_user: dict = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    success = service.remove_member(user_id, team_id, target_user_id)
    if not success:
        raise HTTPException(status_code=403, detail="Unauthorized or cannot remove owner")

@router.post("/{team_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_team(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        success = service.leave_team(user_id, team_id)
        if not success:
            raise HTTPException(status_code=404, detail="Membership not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{team_id}/audit-logs", response_model=List[AuditLog])
def get_audit_logs(
    team_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return service.get_audit_logs(user_id, team_id, limit)

@router.get("/rbac/permission-matrix", response_model=List[PermissionMatrixRow], tags=["rbac"])
def get_permission_matrix():
    return PermissionService.get_matrix()
