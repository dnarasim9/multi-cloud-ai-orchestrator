"""User and RBAC domain models."""

from __future__ import annotations

from enum import Enum

from orchestrator.domain.models.base import DomainEntity


class Role(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    DEPLOYER = "deployer"


class Permission(str, Enum):
    """System permissions."""

    DEPLOYMENT_CREATE = "deployment:create"
    DEPLOYMENT_READ = "deployment:read"
    DEPLOYMENT_APPROVE = "deployment:approve"
    DEPLOYMENT_CANCEL = "deployment:cancel"
    DEPLOYMENT_ROLLBACK = "deployment:rollback"
    DRIFT_SCAN = "drift:scan"
    DRIFT_READ = "drift:read"
    DRIFT_REMEDIATE = "drift:remediate"
    USER_MANAGE = "user:manage"
    SYSTEM_ADMIN = "system:admin"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.OPERATOR: {
        Permission.DEPLOYMENT_CREATE, Permission.DEPLOYMENT_READ,
        Permission.DEPLOYMENT_APPROVE, Permission.DEPLOYMENT_CANCEL,
        Permission.DEPLOYMENT_ROLLBACK, Permission.DRIFT_SCAN,
        Permission.DRIFT_READ, Permission.DRIFT_REMEDIATE,
    },
    Role.DEPLOYER: {
        Permission.DEPLOYMENT_CREATE, Permission.DEPLOYMENT_READ,
        Permission.DRIFT_READ,
    },
    Role.VIEWER: {
        Permission.DEPLOYMENT_READ, Permission.DRIFT_READ,
    },
}


class User(DomainEntity):
    """System user entity."""

    username: str
    email: str
    hashed_password: str = ""
    role: Role = Role.VIEWER
    tenant_id: str = "default"
    is_active: bool = True

    def has_permission(self, permission: Permission) -> bool:
        if not self.is_active:
            return False
        role_perms = ROLE_PERMISSIONS.get(self.role, set())
        return permission in role_perms

    def has_any_permission(self, *permissions: Permission) -> bool:
        return any(self.has_permission(p) for p in permissions)
