"""Task repository implementation."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator.domain.models.cloud_provider import CloudProviderType
from orchestrator.domain.models.task import Task, TaskStatus
from orchestrator.domain.ports.repositories import TaskRepository
from orchestrator.infrastructure.persistence.models import TaskORM


class PostgresTaskRepository(TaskRepository):
    """PostgreSQL implementation of TaskRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, task: Task) -> Task:
        orm = self._to_orm(task)
        self._session.add(orm)
        await self._session.flush()
        return task

    async def get_by_id(self, task_id: str) -> Task | None:
        result = await self._session.execute(
            select(TaskORM).where(TaskORM.id == task_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_deployment(self, deployment_id: str) -> list[Task]:
        result = await self._session.execute(
            select(TaskORM)
            .where(TaskORM.deployment_id == deployment_id)
            .order_by(TaskORM.created_at.asc())
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def list_by_status(self, status: TaskStatus, limit: int = 50) -> list[Task]:
        result = await self._session.execute(
            select(TaskORM)
            .where(TaskORM.status == status.value)
            .order_by(TaskORM.created_at.asc())
            .limit(limit)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def update(self, task: Task) -> Task:
        orm_data = {
            "status": task.status.value,
            "worker_id": task.worker_id,
            "attempt_number": task.attempt_number,
            "output_data": task.output_data,
            "error_message": task.error_message,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "version": task.version,
        }
        await self._session.execute(
            update(TaskORM).where(TaskORM.id == task.id).values(**orm_data)
        )
        return task

    async def acquire_next(self, worker_id: str) -> Task | None:
        """Atomically acquire next queued task using SELECT FOR UPDATE SKIP LOCKED."""
        result = await self._session.execute(
            select(TaskORM)
            .where(TaskORM.status == TaskStatus.QUEUED.value)
            .order_by(TaskORM.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            return None

        orm.status = TaskStatus.ACQUIRED.value
        orm.worker_id = worker_id
        await self._session.flush()
        return self._to_domain(orm)

    async def list_by_worker(self, worker_id: str) -> list[Task]:
        result = await self._session.execute(
            select(TaskORM)
            .where(TaskORM.worker_id == worker_id)
            .order_by(TaskORM.created_at.asc())
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    def _to_orm(self, task: Task) -> TaskORM:
        return TaskORM(
            id=task.id,
            deployment_id=task.deployment_id,
            step_id=task.step_id,
            name=task.name,
            description=task.description,
            status=task.status.value,
            provider=task.provider.value,
            terraform_action=task.terraform_action,
            worker_id=task.worker_id,
            idempotency_key=task.idempotency_key,
            attempt_number=task.attempt_number,
            max_attempts=task.max_attempts,
            timeout_seconds=task.timeout_seconds,
            input_data=task.input_data,
            output_data=task.output_data,
            error_message=task.error_message,
            version=task.version,
        )

    def _to_domain(self, orm: TaskORM) -> Task:
        return Task(
            id=orm.id,
            deployment_id=orm.deployment_id,
            step_id=orm.step_id,
            name=orm.name,
            description=orm.description or "",
            status=TaskStatus(orm.status),
            provider=CloudProviderType(orm.provider),
            terraform_action=orm.terraform_action,
            worker_id=orm.worker_id,
            idempotency_key=orm.idempotency_key,
            attempt_number=orm.attempt_number,
            max_attempts=orm.max_attempts,
            timeout_seconds=orm.timeout_seconds,
            input_data=orm.input_data or {},
            output_data=orm.output_data or {},
            error_message=orm.error_message or "",
            started_at=orm.started_at.isoformat() if orm.started_at else None,
            completed_at=orm.completed_at.isoformat() if orm.completed_at else None,
            version=orm.version,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
