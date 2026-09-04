import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from src.domain.entities.team import Invitation, InvitationCreate, InvitationStatus, RoleEnum, PermissionEnum
from src.infrastructure.persistence.team_models import DBInvitation, DBTeamMember, DBTeam
from src.application.services.permission_service import PermissionService
from src.application.services.team_service import TeamService


class InvitationService:
    def __init__(self, session: Session, team_service: Optional[TeamService] = None):
        self.session = session
        self.team_service = team_service or TeamService(session)

    def _to_entity(self, db_inv: DBInvitation) -> Invitation:
        team_name = db_inv.team.name if db_inv.team else None
        return Invitation(
            id=db_inv.id,
            team_id=db_inv.team_id,
            team_name=team_name,
            email=db_inv.email,
            role=RoleEnum(db_inv.role),
            token=db_inv.token,
            status=InvitationStatus(db_inv.status),
            invited_by=db_inv.invited_by,
            expires_at=db_inv.expires_at,
            created_at=db_inv.created_at,
        )

    def create_invitation(self, actor_id: str, team_id: str, data: InvitationCreate) -> Invitation:
        actor_role = self.team_service.get_user_role_in_team(actor_id, team_id)
        if not actor_role or not PermissionService.has_permission(actor_role, PermissionEnum.ADMIN_INVITE):
            raise PermissionError("User does not have permission to invite members.")

        # Anti-Privilege Escalation
        if not PermissionService.can_assign_role(actor_role, data.role):
            raise ValueError(f"Role '{actor_role.value}' cannot issue invitations for role '{data.role.value}'.")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        db_inv = DBInvitation(
            id=str(uuid.uuid4()),
            team_id=team_id,
            email=data.email.lower().strip(),
            role=data.role.value,
            token=token,
            status=InvitationStatus.PENDING.value,
            invited_by=actor_id,
            expires_at=expires_at,
        )
        self.session.add(db_inv)
        self.team_service._log_audit(
            team_id, actor_id, "INVITATION_SENT", "invitation", db_inv.id,
            {"email": data.email, "role": data.role.value}
        )
        self.session.commit()
        self.session.refresh(db_inv)
        return self._to_entity(db_inv)

    def list_team_invitations(self, actor_id: str, team_id: str) -> List[Invitation]:
        actor_role = self.team_service.get_user_role_in_team(actor_id, team_id)
        if not actor_role or not PermissionService.has_permission(actor_role, PermissionEnum.ADMIN_INVITE):
            return []
        invs = self.session.query(DBInvitation).filter(DBInvitation.team_id == team_id).all()
        return [self._to_entity(i) for i in invs]

    def list_user_invitations(self, user_email: str) -> List[Invitation]:
        invs = (
            self.session.query(DBInvitation)
            .filter(DBInvitation.email == user_email.lower().strip(), DBInvitation.status == InvitationStatus.PENDING.value)
            .all()
        )
        return [self._to_entity(i) for i in invs]

    def accept_invitation(self, user_id: str, token: str) -> bool:
        db_inv = self.session.query(DBInvitation).filter(DBInvitation.token == token).first()
        if not db_inv or db_inv.status != InvitationStatus.PENDING.value:
            return False

        if datetime.now(timezone.utc) > db_inv.expires_at.replace(tzinfo=timezone.utc):
            db_inv.status = InvitationStatus.EXPIRED.value
            self.session.commit()
            return False

        # Add member to team
        member = DBTeamMember(
            id=str(uuid.uuid4()),
            team_id=db_inv.team_id,
            user_id=user_id,
            role=db_inv.role,
        )
        self.session.add(member)
        db_inv.status = InvitationStatus.ACCEPTED.value

        self.team_service._log_audit(
            db_inv.team_id, user_id, "INVITATION_ACCEPTED", "member", user_id,
            {"role": db_inv.role}
        )
        self.session.commit()
        return True

    def reject_invitation(self, user_id: str, token: str) -> bool:
        db_inv = self.session.query(DBInvitation).filter(DBInvitation.token == token).first()
        if not db_inv or db_inv.status != InvitationStatus.PENDING.value:
            return False

        db_inv.status = InvitationStatus.REJECTED.value
        self.team_service._log_audit(
            db_inv.team_id, user_id, "INVITATION_REJECTED", "invitation", db_inv.id
        )
        self.session.commit()
        return True
