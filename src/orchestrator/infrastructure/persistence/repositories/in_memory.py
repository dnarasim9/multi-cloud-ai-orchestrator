"""In-memory repository implementations for development and testing."""

from __future__ import annotations

from orchestrator.domain.models.deployment import Deployment, DeploymentStatus
from orchestrator.domain.models.drift import DriftReport
from orchestrator.domain.models.task import Task, TaskStatus
from orchestrator.domain.models.user import User
from orchestrator.domain.ports.repositories import (
    DeploymentRepository,
    DriftReportRepository,
    TaskRepository,
    UserRepository,
)


# Module-level shared stores enable cross-instance access in the demo API
# while keeping a single clear point for test isolation.
_deployment_store: dict[str, Deployment] = {}
_task_store: dict[str, Task] = {}
_drift_store: dict[str, DriftReport] = {}
_user_store: dict[str, User] = {}


class InMemoryDeploymentRepository(DeploymentRepository):
    """In-memory deployment repository for testing and demo use."""

    def __init__(self) -> None:
        self._store = _deployment_store

    async def save(self, deployment: Deployment) -> Deployment:
        self._store[deployment.id] = deployment
        return deployment

    async def get_by_id(self, deployment_id: str) -> Deployment | None:
        return self._store.get(deployment_id)

    async def list_by_status(
        self, status: DeploymentStatus, limit: int = 50, offset: int = 0
    ) -> list[Deployment]:
        items = [d for d in self._store.values() if d.status == status]
        return sorted(items, key=lambda d: d.created_at, reverse=True)[offset:offset + limit]

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> list[Deployment]:
        items = [d for d in self._store.values() if d.tenant_id == tenant_id]
        return sorted(items, key=lambda d: d.created_at, reverse=True)[offset:offset + limit]

    async def update(self, deployment: Deployment) -> Deployment:
        self._store[deployment.id] = deployment
        return deployment

    async def count_by_status(self, status: DeploymentStatus) -> int:
        return sum(1 for d in self._store.values() if d.status == status)

    @classmethod
    def clear(cls) -> None:
        """Clear the shared store. Used by test fixtures for isolation."""
        _deployment_store.clear()


class InMemoryTaskRepository(TaskRepository):
    """In-memory task repository for testing and demo use."""

    def __init__(self) -> None:
        self._store = _task_store

    async def save(self, task: Task) -> Task:
        self._store[task.id] = task
        return task

    async def get_by_id(self, task_id: str) -> Task | None:
        return self._store.get(task_id)

    async def list_by_deployment(self, deployment_id: str) -> list[Task]:
        return [t for t in self._store.values() if t.deployment_id == deployment_id]

    async def list_by_status(self, status: TaskStatus, limit: int = 50) -> list[Task]:
        items = [t for t in self._store.values() if t.status == status]
        return sorted(items, key=lambda t: t.created_at)[:limit]

    async def update(self, task: Task) -> Task:
        self._store[task.id] = task
        return task

    async def acquire_next(self, worker_id: str) -> Task | None:
        for task in sorted(self._store.values(), key=lambda t: t.created_at):
            if task.status == TaskStatus.QUEUED:
                task.acquire(worker_id)
                self._store[task.id] = task
                return task
        return None

    async def list_by_worker(self, worker_id: str) -> list[Task]:
        return [t for t in self._store.values() if t.worker_id == worker_id]

    @classmethod
    def clear(cls) -> None:
        """Clear the shared store. Used by test fixtures for isolation."""
        _task_store.clear()


class InMemoryDriftReportRepository(DriftReportRepository):
    """In-memory drift report repository for testing and demo use."""

    def __init__(self) -> None:
        self._store = _drift_store

    async def save(self, report: DriftReport) -> DriftReport:
        self._store[report.id] = report
        return report

    async def get_by_id(self, report_id: str) -> DriftReport | None:
        return self._store.get(report_id)

    async def list_by_deployment(
        self, deployment_id: str, limit: int = 20
    ) -> list[DriftReport]:
        items = [r for r in self._store.values() if r.deployment_id == deployment_id]
        return sorted(items, key=lambda r: r.created_at, reverse=True)[:limit]

    async def get_latest_for_deployment(self, deployment_id: str) -> DriftReport | None:
        reports = await self.list_by_deployment(deployment_id, limit=1)
        return reports[0] if reports else None

    @classmethod
    def clear(cls) -> None:
        """Clear the shared store. Used by test fixtures for isolation."""
        _drift_store.clear()


class InMemoryUserRepository(UserRepository):
    """In-memory user repository for testing and demo use."""

    def __init__(self) -> None:
        self._store = _user_store

    async def save(self, user: User) -> User:
        self._store[user.id] = user
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        return self._store.get(user_id)

    async def get_by_username(self, username: str) -> User | None:
        for user in self._store.values():
            if user.username == username:
                return user
        return None

    async def list_by_tenant(self, tenant_id: str) -> list[User]:
        return [u for u in self._store.values() if u.tenant_id == tenant_id]

    async def update(self, user: User) -> User:
        self._store[user.id] = user
        return user

    @classmethod
    def clear(cls) -> None:
        """Clear the shared store. Used by test fixtures for isolation."""
        _user_store.clear()
