import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from src.domain.entities.team import (
    Team, TeamCreate, TeamUpdate, TeamMember, RoleEnum, AuditLog, PermissionEnum
)
from src.infrastructure.persistence.team_models import DBTeam, DBTeamMember, DBAuditLog
from src.application.services.permission_service import PermissionService


class TeamService:
    def __init__(self, session: Session = None, db_session: Session = None):
        self.session = session if session is not None else db_session

    def _log_audit(
        self,
        team_id: str,
        actor_id: str,
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> DBAuditLog:
        log = DBAuditLog(
            id=str(uuid.uuid4()),
            team_id=team_id,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details_json=details or {},
        )
        self.session.add(log)
        return log

    def _resolve_profiles(self, user_ids: List[str]) -> dict:
        """
        Bulk-fetch user profiles for a list of user_ids.
        Returns a dict: { user_id -> {"name": ..., "avatar": ...} }
        Falls back gracefully if user_profiles table is missing or profile not found.
        """
        if not user_ids:
            return {}
        try:
            from src.infrastructure.persistence.user_profile_models import DBUserProfile
            profiles = (
                self.session.query(DBUserProfile)
                .filter(DBUserProfile.user_id.in_(user_ids))
                .all()
            )
            return {
                p.user_id: {
                    "name": p.name or None,
                    "avatar": p.avatar or None,
                }
                for p in profiles
            }
        except Exception:
            return {}

    def _resolve_emails(self, user_ids: List[str]) -> dict:
        """
        Attempt to fetch email addresses from Supabase auth.users via raw SQL.
        Returns a dict: { user_id -> email_str }
        Silently returns empty dict if unavailable (e.g. dev/test mode).
        """
        if not user_ids:
            return {}
        try:
            from sqlalchemy import text
            placeholders = ", ".join([f"'{uid}'" for uid in user_ids])
            sql = text(f"SELECT id, email FROM auth.users WHERE id IN ({placeholders})")
            rows = self.session.execute(sql).fetchall()
            return {str(r[0]): r[1] for r in rows}
        except Exception:
            return {}

    def _to_entity(self, db_team: DBTeam) -> Team:
        member_user_ids = [m.user_id for m in (db_team.members or [])]

        # Bulk resolve profiles and emails (no N+1)
        profiles = self._resolve_profiles(member_user_ids)
        emails = self._resolve_emails(member_user_ids)

        members = []
        for m in (db_team.members or []):
            profile = profiles.get(m.user_id, {})
            email = emails.get(m.user_id) or None

            # Prefer profile name; fall back to email prefix; never show raw UUID as name
            raw_name = profile.get("name")
            if raw_name:
                display_name = raw_name
            elif email:
                display_name = email.split("@")[0]
            else:
                display_name = None  # frontend shows "Unknown Member"

            members.append(TeamMember(
                id=m.id,
                team_id=m.team_id,
                user_id=m.user_id,
                role=RoleEnum(m.role),
                email=email,
                name=display_name,
                avatar=profile.get("avatar"),
                joined_at=m.joined_at,
            ))

        return Team(
            id=db_team.id,
            name=db_team.name,
            description=db_team.description,
            owner_id=db_team.owner_id,
            member_count=len(members),
            members=members,
            created_at=db_team.created_at or datetime.now(),
            updated_at=db_team.updated_at or db_team.created_at or datetime.now(),
        )

    def get_user_role_in_team(self, user_id: str, team_id: str) -> Optional[RoleEnum]:
        member = (
            self.session.query(DBTeamMember)
            .filter(DBTeamMember.team_id == team_id, DBTeamMember.user_id == user_id)
            .first()
        )
        return RoleEnum(member.role) if member else None

    def create_team(self, user_id: str, data: TeamCreate) -> Team:
        team_id = str(uuid.uuid4())
        db_team = DBTeam(
            id=team_id,
            name=data.name,
            description=data.description,
            owner_id=user_id,
        )
        self.session.add(db_team)
        self.session.flush()

        # Add creator as OWNER
        owner_member = DBTeamMember(
            id=str(uuid.uuid4()),
            team_id=team_id,
            user_id=user_id,
            role=RoleEnum.OWNER.value,
        )
        self.session.add(owner_member)

        # Audit log
        self._log_audit(team_id, user_id, "TEAM_CREATED", "team", team_id, {"name": data.name})

        self.session.commit()
        self.session.refresh(db_team)
        return self._to_entity(db_team)

    def get_team(self, team_id: str) -> Optional[Team]:
        db_team = self.session.query(DBTeam).filter(DBTeam.id == team_id).first()
        return self._to_entity(db_team) if db_team else None

    def list_user_teams(self, user_id: str) -> List[Team]:
        memberships = self.session.query(DBTeamMember).filter(DBTeamMember.user_id == user_id).all()
        team_ids = [m.team_id for m in memberships]
        if not team_ids:
            return []
        db_teams = self.session.query(DBTeam).filter(DBTeam.id.in_(team_ids)).all()
        return [self._to_entity(t) for t in db_teams]

    def update_team(self, actor_id: str, team_id: str, data: TeamUpdate) -> Optional[Team]:
        role = self.get_user_role_in_team(actor_id, team_id)
        if not role or not PermissionService.has_permission(role, PermissionEnum.ADMIN_MANAGE_TEAM):
            return None

        db_team = self.session.query(DBTeam).filter(DBTeam.id == team_id).first()
        if not db_team:
            return None

        if data.name:
            db_team.name = data.name
        if data.description is not None:
            db_team.description = data.description

        self._log_audit(team_id, actor_id, "TEAM_UPDATED", "team", team_id, data.model_dump(exclude_unset=True))
        self.session.commit()
        self.session.refresh(db_team)
        return self._to_entity(db_team)

    def delete_team(self, actor_id: str, team_id: str) -> bool:
        role = self.get_user_role_in_team(actor_id, team_id)
        if role != RoleEnum.OWNER:
            return False  # Only OWNER can delete team

        db_team = self.session.query(DBTeam).filter(DBTeam.id == team_id).first()
        if not db_team:
            return False

        self._log_audit(team_id, actor_id, "TEAM_DELETED", "team", team_id)
        self.session.delete(db_team)
        self.session.commit()
        return True

    def transfer_ownership(self, actor_id: str, team_id: str, new_owner_id: str) -> Optional[Team]:
        actor_role = self.get_user_role_in_team(actor_id, team_id)
        if actor_role != RoleEnum.OWNER:
            return None

        target_member = (
            self.session.query(DBTeamMember)
            .filter(DBTeamMember.team_id == team_id, DBTeamMember.user_id == new_owner_id)
            .first()
        )
        if not target_member:
            return None

        actor_member = (
            self.session.query(DBTeamMember)
            .filter(DBTeamMember.team_id == team_id, DBTeamMember.user_id == actor_id)
            .first()
        )

        db_team = self.session.query(DBTeam).filter(DBTeam.id == team_id).first()
        if not db_team:
            return None

        # Promote target to OWNER, demote actor to ADMIN
        target_member.role = RoleEnum.OWNER.value
        if actor_member:
            actor_member.role = RoleEnum.ADMIN.value
        db_team.owner_id = new_owner_id

        self._log_audit(team_id, actor_id, "OWNERSHIP_TRANSFERRED", "team", team_id, {"new_owner_id": new_owner_id})
        self.session.commit()
        self.session.refresh(db_team)
        return self._to_entity(db_team)

    def change_member_role(self, actor_id: str, team_id: str, target_user_id: str, new_role: RoleEnum) -> Optional[TeamMember]:
        actor_role = self.get_user_role_in_team(actor_id, team_id)
        if not actor_role or not PermissionService.has_permission(actor_role, PermissionEnum.ADMIN_CHANGE_ROLE):
            return None

        # Anti-Privilege Escalation Check
        if not PermissionService.can_assign_role(actor_role, new_role):
            raise ValueError(f"Role '{actor_role.value}' cannot assign role '{new_role.value}' due to privilege escalation controls.")

        target_member = (
            self.session.query(DBTeamMember)
            .filter(DBTeamMember.team_id == team_id, DBTeamMember.user_id == target_user_id)
            .first()
        )
        if not target_member:
            return None

        old_role = target_member.role
        target_member.role = new_role.value

        self._log_audit(
            team_id, actor_id, "MEMBER_ROLE_CHANGED", "member", target_user_id,
            {"old_role": old_role, "new_role": new_role.value}
        )
        self.session.commit()
        self.session.refresh(target_member)

        # Resolve profile for returned member
        profiles = self._resolve_profiles([target_member.user_id])
        emails = self._resolve_emails([target_member.user_id])
        profile = profiles.get(target_member.user_id, {})
        email = emails.get(target_member.user_id)
        raw_name = profile.get("name")
        display_name = raw_name or (email.split("@")[0] if email else None)

        return TeamMember(
            id=target_member.id,
            team_id=target_member.team_id,
            user_id=target_member.user_id,
            role=RoleEnum(target_member.role),
            email=email,
            name=display_name,
            avatar=profile.get("avatar"),
            joined_at=target_member.joined_at,
        )

    def remove_member(self, actor_id: str, team_id: str, target_user_id: str) -> bool:
        actor_role = self.get_user_role_in_team(actor_id, team_id)
        if not actor_role or not PermissionService.has_permission(actor_role, PermissionEnum.ADMIN_REMOVE_MEMBER):
            return False

        target_member = (
            self.session.query(DBTeamMember)
            .filter(DBTeamMember.team_id == team_id, DBTeamMember.user_id == target_user_id)
            .first()
        )
        if not target_member or target_member.role == RoleEnum.OWNER.value:
            return False  # Cannot remove team OWNER

        self.session.delete(target_member)
        self._log_audit(team_id, actor_id, "MEMBER_REMOVED", "member", target_user_id)
        self.session.commit()
        return True

    def leave_team(self, user_id: str, team_id: str) -> bool:
        role = self.get_user_role_in_team(user_id, team_id)
        if role == RoleEnum.OWNER:
            raise ValueError("Owner cannot leave team. Transfer ownership first or delete team.")

        target_member = (
            self.session.query(DBTeamMember)
            .filter(DBTeamMember.team_id == team_id, DBTeamMember.user_id == user_id)
            .first()
        )
        if not target_member:
            return False

        self.session.delete(target_member)
        self._log_audit(team_id, user_id, "MEMBER_LEFT", "member", user_id)
        self.session.commit()
        return True

    def get_audit_logs(self, actor_id: str, team_id: str, limit: int = 50) -> List[AuditLog]:
        role = self.get_user_role_in_team(actor_id, team_id)
        if not role:
            return []
        logs = (
            self.session.query(DBAuditLog)
            .filter(DBAuditLog.team_id == team_id)
            .order_by(DBAuditLog.created_at.desc())
            .limit(limit)
            .all()
        )

        # Bulk-resolve actor profiles (one query per type, not N queries)
        actor_ids = list({l.actor_id for l in logs})
        profiles = self._resolve_profiles(actor_ids)
        emails = self._resolve_emails(actor_ids)

        result = []
        for l in logs:
            profile = profiles.get(l.actor_id, {})
            email = emails.get(l.actor_id)
            raw_name = profile.get("name")
            actor_name = raw_name or (email.split("@")[0] if email else None)

            result.append(AuditLog(
                id=l.id,
                team_id=l.team_id,
                actor_id=l.actor_id,
                actor_name=actor_name,
                actor_email=email,
                action=l.action,
                target_type=l.target_type,
                target_id=l.target_id,
                details_json=l.details_json or {},
                created_at=l.created_at,
            ))
        return result
