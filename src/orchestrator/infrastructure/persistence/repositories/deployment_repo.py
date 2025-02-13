"""Deployment repository implementation."""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator.domain.models.deployment import (
    Deployment,
    DeploymentIntent,
    DeploymentStatus,
    ExecutionPlan,
    StepResult,
)
from orchestrator.domain.ports.repositories import DeploymentRepository
from orchestrator.infrastructure.persistence.models import DeploymentORM


class PostgresDeploymentRepository(DeploymentRepository):
    """PostgreSQL implementation of DeploymentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, deployment: Deployment) -> Deployment:
        orm = self._to_orm(deployment)
        self._session.add(orm)
        await self._session.flush()
        return deployment

    async def get_by_id(self, deployment_id: str) -> Deployment | None:
        result = await self._session.execute(
            select(DeploymentORM).where(DeploymentORM.id == deployment_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_status(
        self, status: DeploymentStatus, limit: int = 50, offset: int = 0
    ) -> list[Deployment]:
        result = await self._session.execute(
            select(DeploymentORM)
            .where(DeploymentORM.status == status.value)
            .order_by(DeploymentORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> list[Deployment]:
        result = await self._session.execute(
            select(DeploymentORM)
            .where(DeploymentORM.tenant_id == tenant_id)
            .order_by(DeploymentORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def update(self, deployment: Deployment) -> Deployment:
        orm_data = {
            "name": deployment.name,
            "status": deployment.status.value,
            "intent_data": deployment.intent.model_dump(),
            "plan_data": deployment.plan.model_dump() if deployment.plan else None,
            "step_results_data": [r.model_dump() for r in deployment.step_results],
            "error_message": deployment.error_message,
            "rollback_deployment_id": deployment.rollback_deployment_id,
            "version": deployment.version,
        }
        await self._session.execute(
            update(DeploymentORM)
            .where(DeploymentORM.id == deployment.id)
            .values(**orm_data)
        )
        return deployment

    async def count_by_status(self, status: DeploymentStatus) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(DeploymentORM).where(
                DeploymentORM.status == status.value
            )
        )
        return result.scalar_one()

    def _to_orm(self, deployment: Deployment) -> DeploymentORM:
        return DeploymentORM(
            id=deployment.id,
            name=deployment.name,
            status=deployment.status.value,
            intent_data=deployment.intent.model_dump(),
            plan_data=deployment.plan.model_dump() if deployment.plan else None,
            step_results_data=[r.model_dump() for r in deployment.step_results],
            initiated_by=deployment.initiated_by,
            tenant_id=deployment.tenant_id,
            error_message=deployment.error_message,
            rollback_deployment_id=deployment.rollback_deployment_id,
            version=deployment.version,
        )

    def _to_domain(self, orm: DeploymentORM) -> Deployment:
        plan = None
        if orm.plan_data:
            plan = ExecutionPlan.model_validate(orm.plan_data)

        step_results = []
        if orm.step_results_data:
            step_results = [StepResult.model_validate(r) for r in orm.step_results_data]

        return Deployment(
            id=orm.id,
            name=orm.name,
            status=DeploymentStatus(orm.status),
            intent=DeploymentIntent.model_validate(orm.intent_data),
            plan=plan,
            step_results=step_results,
            initiated_by=orm.initiated_by,
            tenant_id=orm.tenant_id,
            error_message=orm.error_message or "",
            rollback_deployment_id=orm.rollback_deployment_id,
            version=orm.version,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
