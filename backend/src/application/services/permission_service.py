from typing import Dict, Set, List
from src.domain.entities.team import RoleEnum, PermissionEnum, PermissionMatrixRow

# ---------------------------------------------------------------------------
# Standard RBAC Permission Matrix Mapping
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: Dict[RoleEnum, Set[PermissionEnum]] = {
    RoleEnum.OWNER: {
        # All permissions
        PermissionEnum.WORKSPACE_READ, PermissionEnum.WORKSPACE_WRITE,
        PermissionEnum.WORKSPACE_DELETE, PermissionEnum.WORKSPACE_MANAGE,
        PermissionEnum.REPO_READ, PermissionEnum.REPO_CLONE, PermissionEnum.REPO_EDIT,
        PermissionEnum.REPO_DELETE, PermissionEnum.REPO_INDEX,
        PermissionEnum.AI_CHAT, PermissionEnum.AI_TOOL_CALL,
        PermissionEnum.AI_MEMORY, PermissionEnum.AI_AGENT_EXEC,
        PermissionEnum.ADMIN_INVITE, PermissionEnum.ADMIN_REMOVE_MEMBER,
        PermissionEnum.ADMIN_CHANGE_ROLE, PermissionEnum.ADMIN_MANAGE_TEAM,
    },
    RoleEnum.ADMIN: {
        PermissionEnum.WORKSPACE_READ, PermissionEnum.WORKSPACE_WRITE,
        PermissionEnum.WORKSPACE_MANAGE,
        PermissionEnum.REPO_READ, PermissionEnum.REPO_CLONE, PermissionEnum.REPO_EDIT,
        PermissionEnum.REPO_INDEX,
        PermissionEnum.AI_CHAT, PermissionEnum.AI_TOOL_CALL,
        PermissionEnum.AI_MEMORY, PermissionEnum.AI_AGENT_EXEC,
        PermissionEnum.ADMIN_INVITE, PermissionEnum.ADMIN_REMOVE_MEMBER,
        PermissionEnum.ADMIN_CHANGE_ROLE, PermissionEnum.ADMIN_MANAGE_TEAM,
    },
    RoleEnum.MAINTAINER: {
        PermissionEnum.WORKSPACE_READ, PermissionEnum.WORKSPACE_WRITE,
        PermissionEnum.REPO_READ, PermissionEnum.REPO_CLONE, PermissionEnum.REPO_EDIT,
        PermissionEnum.REPO_INDEX,
        PermissionEnum.AI_CHAT, PermissionEnum.AI_TOOL_CALL,
        PermissionEnum.AI_MEMORY, PermissionEnum.AI_AGENT_EXEC,
        PermissionEnum.ADMIN_INVITE,
    },
    RoleEnum.DEVELOPER: {
        PermissionEnum.WORKSPACE_READ, PermissionEnum.WORKSPACE_WRITE,
        PermissionEnum.REPO_READ, PermissionEnum.REPO_CLONE,
        PermissionEnum.AI_CHAT, PermissionEnum.AI_TOOL_CALL,
        PermissionEnum.AI_MEMORY, PermissionEnum.AI_AGENT_EXEC,
    },
    RoleEnum.REVIEWER: {
        PermissionEnum.WORKSPACE_READ,
        PermissionEnum.REPO_READ,
        PermissionEnum.AI_CHAT, PermissionEnum.AI_MEMORY,
    },
    RoleEnum.VIEWER: {
        PermissionEnum.WORKSPACE_READ,
        PermissionEnum.REPO_READ,
    },
}

# Numerical rank for role hierarchy comparisons (lower index = higher rank)
ROLE_RANK: Dict[RoleEnum, int] = {
    RoleEnum.OWNER: 0,
    RoleEnum.ADMIN: 1,
    RoleEnum.MAINTAINER: 2,
    RoleEnum.DEVELOPER: 3,
    RoleEnum.REVIEWER: 4,
    RoleEnum.VIEWER: 5,
}

PERMISSION_METADATA: List[tuple[PermissionEnum, str, str]] = [
    (PermissionEnum.WORKSPACE_READ, "Workspace", "Read workspace contents and settings"),
    (PermissionEnum.WORKSPACE_WRITE, "Workspace", "Create and modify workspace resources"),
    (PermissionEnum.WORKSPACE_DELETE, "Workspace", "Permanently delete workspace"),
    (PermissionEnum.WORKSPACE_MANAGE, "Workspace", "Configure workspace policies and defaults"),
    (PermissionEnum.REPO_READ, "Repository", "View repository code and branches"),
    (PermissionEnum.REPO_CLONE, "Repository", "Clone or download repository code"),
    (PermissionEnum.REPO_EDIT, "Repository", "Edit repository details and metadata"),
    (PermissionEnum.REPO_DELETE, "Repository", "Delete repository from system"),
    (PermissionEnum.REPO_INDEX, "Repository", "Trigger AI code re-indexing"),
    (PermissionEnum.AI_CHAT, "AI Engine", "Interact with AI Chat & Co-Pilot"),
    (PermissionEnum.AI_TOOL_CALL, "AI Engine", "Execute automated agent tool calls"),
    (PermissionEnum.AI_MEMORY, "AI Engine", "View and access intelligent memory"),
    (PermissionEnum.AI_AGENT_EXEC, "AI Engine", "Trigger autonomous multi-agent workflows"),
    (PermissionEnum.ADMIN_INVITE, "Administration", "Invite new team members"),
    (PermissionEnum.ADMIN_REMOVE_MEMBER, "Administration", "Remove members from team"),
    (PermissionEnum.ADMIN_CHANGE_ROLE, "Administration", "Modify member roles"),
    (PermissionEnum.ADMIN_MANAGE_TEAM, "Administration", "Edit or delete team settings"),
]


class PermissionService:
    @staticmethod
    def get_role_permissions(role: RoleEnum) -> Set[PermissionEnum]:
        return ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def has_permission(role: RoleEnum, permission: PermissionEnum) -> bool:
        return permission in ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def can_assign_role(actor_role: RoleEnum, target_role: RoleEnum) -> bool:
        """
        Prevents privilege escalation.
        Actors can only assign roles of STRICTLY LOWER rank than their own,
        except OWNER who can assign any role.
        """
        if actor_role == RoleEnum.OWNER:
            return True
        actor_rank = ROLE_RANK.get(actor_role, 99)
        target_rank = ROLE_RANK.get(target_role, 99)
        return actor_rank < target_rank

    @staticmethod
    def can_manage_role(actor_role: RoleEnum, target_role: RoleEnum) -> bool:
        if actor_role not in (RoleEnum.OWNER, RoleEnum.ADMIN):
            return False
        return PermissionService.can_assign_role(actor_role, target_role)

    @staticmethod
    def get_matrix() -> List[PermissionMatrixRow]:
        rows: List[PermissionMatrixRow] = []
        for perm, category, desc in PERMISSION_METADATA:
            role_map = {r: perm in ROLE_PERMISSIONS[r] for r in RoleEnum}
            rows.append(PermissionMatrixRow(
                permission=perm,
                category=category,
                description=desc,
                roles=role_map,
            ))
        return rows
