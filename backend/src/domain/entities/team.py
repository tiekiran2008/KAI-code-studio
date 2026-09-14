from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RoleEnum(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MAINTAINER = "maintainer"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class PermissionEnum(str, Enum):
    # Workspace permissions
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_WRITE = "workspace:write"
    WORKSPACE_DELETE = "workspace:delete"
    WORKSPACE_MANAGE = "workspace:manage"

    # Repository permissions
    REPO_READ = "repo:read"
    REPO_CLONE = "repo:clone"
    REPO_EDIT = "repo:edit"
    REPO_DELETE = "repo:delete"
    REPO_INDEX = "repo:index"

    # AI permissions
    AI_CHAT = "ai:chat"
    AI_TOOL_CALL = "ai:tool_call"
    AI_MEMORY = "ai:memory"
    AI_AGENT_EXEC = "ai:agent_exec"

    # Administration permissions
    ADMIN_INVITE = "admin:invite"
    ADMIN_REMOVE_MEMBER = "admin:remove_member"
    ADMIN_CHANGE_ROLE = "admin:change_role"
    ADMIN_MANAGE_TEAM = "admin:manage_team"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ---------------------------------------------------------------------------
# Pydantic Domain Entities
# ---------------------------------------------------------------------------

class TeamMemberBase(BaseModel):
    user_id: str
    role: RoleEnum = RoleEnum.DEVELOPER
    email: Optional[str] = None
    name: Optional[str] = None
    avatar: Optional[str] = None


class TeamMember(TeamMemberBase):
    id: str
    team_id: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TransferOwnership(BaseModel):
    new_owner_user_id: str


class Team(TeamBase):
    id: str
    owner_id: str
    member_count: int = 1
    members: List[TeamMember] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationCreate(BaseModel):
    email: str = Field(..., min_length=3, description="Email address of user to invite")
    role: RoleEnum = RoleEnum.DEVELOPER


class Invitation(BaseModel):
    id: str
    team_id: str
    team_name: Optional[str] = None
    email: str
    role: RoleEnum
    token: str
    status: InvitationStatus = InvitationStatus.PENDING
    invited_by: str
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberRoleUpdate(BaseModel):
    role: RoleEnum


class AuditLog(BaseModel):
    id: str
    team_id: str
    actor_id: str
    actor_name: Optional[str] = None   # Resolved from user_profiles; never raw UUID
    actor_email: Optional[str] = None  # Resolved from user_profiles
    action: str
    target_type: str
    target_id: Optional[str] = None
    details_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionMatrixRow(BaseModel):
    permission: PermissionEnum
    category: str
    description: str
    roles: Dict[RoleEnum, bool]
