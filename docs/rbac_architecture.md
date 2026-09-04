# Role-Based Access Control (RBAC) Architecture

## Overview
Phase 10.5 introduces a comprehensive RBAC system for the AI Agent platform.

## Roles
The system defines 6 hierarchical roles:
1. **Owner**: Full control over the team, can transfer ownership, delete team, manage all roles.
2. **Admin**: Can manage members, invite users, edit team settings, manage roles up to Maintainer.
3. **Maintainer**: Can manage workspaces, repositories, index code, execute agents.
4. **Developer**: Can read/write workspace code, execute AI agents, tool calls, RAG queries.
5. **Reviewer**: Can read code, review PRs/code, execute AI chat, view memory.
6. **Viewer**: Read-only access to workspaces, repos, and public team info.

## Permissions Map
Permissions are grouped by categories (Workspace, Repository, AI Engine, Administration). Each role is mapped to specific permissions defined in `PermissionEnum`.

## Validation Logic
The `PermissionService` enforces two primary rules:
1. `has_permission(role, permission)`: Checks if the user's role grants the requested permission.
2. `can_manage_role(actor_role, target_role)`: Ensures a user can only assign or remove roles that are strictly beneath them in the hierarchy.

## Audit Logs
All administrative actions (role changes, team transfers, member removals) generate an `AuditLog` entry for security tracking.
