from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.domain.entities.team import Invitation, InvitationCreate
from src.application.services.invitation_service import InvitationService
from src.interfaces.api.dependencies import get_current_user

router = APIRouter(tags=["invitations"])

engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_invitation_service(db: Session = Depends(get_db)) -> InvitationService:
    return InvitationService(db)

@router.post("/teams/{team_id}/invitations", response_model=Invitation, status_code=status.HTTP_201_CREATED)
def invite_member(
    team_id: str,
    data: InvitationCreate,
    current_user: dict = Depends(get_current_user),
    service: InvitationService = Depends(get_invitation_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        return service.create_invitation(user_id, team_id, data)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/teams/{team_id}/invitations", response_model=List[Invitation])
def list_team_invitations(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    service: InvitationService = Depends(get_invitation_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return service.list_team_invitations(user_id, team_id)

@router.get("/invitations", response_model=List[Invitation])
def list_user_invitations(
    current_user: dict = Depends(get_current_user),
    service: InvitationService = Depends(get_invitation_service),
):
    # Typically user's email is in JWT payload
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="User email not found in token")
    return service.list_user_invitations(email)

@router.post("/invitations/{token}/accept", status_code=status.HTTP_204_NO_CONTENT)
def accept_invitation(
    token: str,
    current_user: dict = Depends(get_current_user),
    service: InvitationService = Depends(get_invitation_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    success = service.accept_invitation(user_id, token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation token")

@router.post("/invitations/{token}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_invitation(
    token: str,
    current_user: dict = Depends(get_current_user),
    service: InvitationService = Depends(get_invitation_service),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    success = service.reject_invitation(user_id, token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid invitation token")
