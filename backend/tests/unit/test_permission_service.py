import pytest
from src.domain.entities.team import RoleEnum, PermissionEnum
from src.application.services.permission_service import PermissionService

@pytest.fixture
def permission_service():
    return PermissionService()

def test_owner_has_all_permissions(permission_service):
    for permission in PermissionEnum:
        assert permission_service.has_permission(RoleEnum.OWNER, permission) is True

def test_viewer_has_limited_permissions(permission_service):
    assert permission_service.has_permission(RoleEnum.VIEWER, PermissionEnum.WORKSPACE_READ) is True
    assert permission_service.has_permission(RoleEnum.VIEWER, PermissionEnum.REPO_READ) is True
    
    assert permission_service.has_permission(RoleEnum.VIEWER, PermissionEnum.WORKSPACE_WRITE) is False
    assert permission_service.has_permission(RoleEnum.VIEWER, PermissionEnum.ADMIN_INVITE) is False

def test_developer_has_standard_permissions(permission_service):
    assert permission_service.has_permission(RoleEnum.DEVELOPER, PermissionEnum.WORKSPACE_WRITE) is True
    assert permission_service.has_permission(RoleEnum.DEVELOPER, PermissionEnum.AI_CHAT) is True
    assert permission_service.has_permission(RoleEnum.DEVELOPER, PermissionEnum.AI_AGENT_EXEC) is True
    
    assert permission_service.has_permission(RoleEnum.DEVELOPER, PermissionEnum.ADMIN_MANAGE_TEAM) is False

def test_admin_permissions(permission_service):
    assert permission_service.has_permission(RoleEnum.ADMIN, PermissionEnum.ADMIN_INVITE) is True
    assert permission_service.has_permission(RoleEnum.ADMIN, PermissionEnum.ADMIN_CHANGE_ROLE) is True
    
def test_hierarchy_validation(permission_service):
    # Owner can manage Admin
    assert permission_service.can_manage_role(RoleEnum.OWNER, RoleEnum.ADMIN) is True
    # Admin can manage Developer
    assert permission_service.can_manage_role(RoleEnum.ADMIN, RoleEnum.DEVELOPER) is True
    # Admin cannot manage Owner
    assert permission_service.can_manage_role(RoleEnum.ADMIN, RoleEnum.OWNER) is False
    # Developer cannot manage anyone
    assert permission_service.can_manage_role(RoleEnum.DEVELOPER, RoleEnum.VIEWER) is False
