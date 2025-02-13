"""User repository implementation."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator.domain.models.user import Role, User
from orchestrator.domain.ports.repositories import UserRepository
from orchestrator.infrastructure.persistence.models import UserORM


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user: User) -> User:
        orm = self._to_orm(user)
        self._session.add(orm)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(
            select(UserORM).where(UserORM.id == user_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(
            select(UserORM).where(UserORM.username == username)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_tenant(self, tenant_id: str) -> list[User]:
        result = await self._session.execute(
            select(UserORM)
            .where(UserORM.tenant_id == tenant_id)
            .order_by(UserORM.username.asc())
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def update(self, user: User) -> User:
        orm_data = {
            "username": user.username,
            "email": user.email,
            "hashed_password": user.hashed_password,
            "role": user.role.value,
            "is_active": user.is_active,
            "version": user.version,
        }
        await self._session.execute(
            update(UserORM).where(UserORM.id == user.id).values(**orm_data)
        )
        return user

    def _to_orm(self, user: User) -> UserORM:
        return UserORM(
            id=user.id,
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password,
            role=user.role.value,
            tenant_id=user.tenant_id,
            is_active=user.is_active,
            version=user.version,
        )

    def _to_domain(self, orm: UserORM) -> User:
        return User(
            id=orm.id,
            username=orm.username,
            email=orm.email,
            hashed_password=orm.hashed_password,
            role=Role(orm.role),
            tenant_id=orm.tenant_id,
            is_active=orm.is_active,
            version=orm.version,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
