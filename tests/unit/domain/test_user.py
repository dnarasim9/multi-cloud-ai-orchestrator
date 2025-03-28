"""Unit tests for user domain model."""

from __future__ import annotations

from orchestrator.domain.models.user import Permission, Role, ROLE_PERMISSIONS, User


class TestUser:
    def test_admin_has_all_permissions(self) -> None:
        user = User(
            username="admin",
            email="admin@test.com",
            role=Role.ADMIN,
        )
        for perm in Permission:
            assert user.has_permission(perm)

    def test_viewer_cannot_create_deployment(self) -> None:
        user = User(
            username="viewer",
            email="viewer@test.com",
            role=Role.VIEWER,
        )
        assert not user.has_permission(Permission.DEPLOYMENT_CREATE)
        assert user.has_permission(Permission.DEPLOYMENT_READ)

    def test_deployer_permissions(self) -> None:
        user = User(
            username="deployer",
            email="deployer@test.com",
            role=Role.DEPLOYER,
        )
        assert user.has_permission(Permission.DEPLOYMENT_CREATE)
        assert user.has_permission(Permission.DEPLOYMENT_READ)
        assert not user.has_permission(Permission.DEPLOYMENT_APPROVE)

    def test_inactive_user_no_permissions(self) -> None:
        user = User(
            username="inactive",
            email="inactive@test.com",
            role=Role.ADMIN,
            is_active=False,
        )
        assert not user.has_permission(Permission.SYSTEM_ADMIN)

    def test_has_any_permission(self) -> None:
        user = User(
            username="viewer",
            email="viewer@test.com",
            role=Role.VIEWER,
        )
        assert user.has_any_permission(
            Permission.DEPLOYMENT_READ,
            Permission.DEPLOYMENT_CREATE,
        )
        assert not user.has_any_permission(
            Permission.DEPLOYMENT_CREATE,
            Permission.SYSTEM_ADMIN,
        )

    def test_all_roles_have_permissions_defined(self) -> None:
        for role in Role:
            assert role in ROLE_PERMISSIONS
