"""Repository port interfaces (hexagonal architecture)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from orchestrator.domain.models.deployment import Deployment, DeploymentStatus
from orchestrator.domain.models.drift import DriftReport
from orchestrator.domain.models.task import Task, TaskStatus
from orchestrator.domain.models.user import User


class DeploymentRepository(ABC):
    """Port for deployment persistence."""

    @abstractmethod
    async def save(self, deployment: Deployment) -> Deployment:
        """Persist a deployment."""

    @abstractmethod
    async def get_by_id(self, deployment_id: str) -> Deployment | None:
        """Retrieve a deployment by ID."""

    @abstractmethod
    async def list_by_status(
        self, status: DeploymentStatus, limit: int = 50, offset: int = 0
    ) -> list[Deployment]:
        """List deployments by status."""

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> list[Deployment]:
        """List deployments for a tenant."""

    @abstractmethod
    async def update(self, deployment: Deployment) -> Deployment:
        """Update an existing deployment."""

    @abstractmethod
    async def count_by_status(self, status: DeploymentStatus) -> int:
        """Count deployments by status."""


class TaskRepository(ABC):
    """Port for task persistence."""

    @abstractmethod
    async def save(self, task: Task) -> Task:
        """Persist a task."""

    @abstractmethod
    async def get_by_id(self, task_id: str) -> Task | None:
        """Retrieve a task by ID."""

    @abstractmethod
    async def list_by_deployment(self, deployment_id: str) -> list[Task]:
        """List all tasks for a deployment."""

    @abstractmethod
    async def list_by_status(self, status: TaskStatus, limit: int = 50) -> list[Task]:
        """List tasks by status."""

    @abstractmethod
    async def update(self, task: Task) -> Task:
        """Update an existing task."""

    @abstractmethod
    async def acquire_next(self, worker_id: str) -> Task | None:
        """Atomically acquire the next queued task."""

    @abstractmethod
    async def list_by_worker(self, worker_id: str) -> list[Task]:
        """List tasks assigned to a worker."""


class DriftReportRepository(ABC):
    """Port for drift report persistence."""

    @abstractmethod
    async def save(self, report: DriftReport) -> DriftReport:
        """Persist a drift report."""

    @abstractmethod
    async def get_by_id(self, report_id: str) -> DriftReport | None:
        """Retrieve a drift report by ID."""

    @abstractmethod
    async def list_by_deployment(
        self, deployment_id: str, limit: int = 20
    ) -> list[DriftReport]:
        """List drift reports for a deployment."""

    @abstractmethod
    async def get_latest_for_deployment(self, deployment_id: str) -> DriftReport | None:
        """Get the most recent drift report for a deployment."""


class UserRepository(ABC):
    """Port for user persistence."""

    @abstractmethod
    async def save(self, user: User) -> User:
        """Persist a user."""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        """Retrieve a user by ID."""

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        """Retrieve a user by username."""

    @abstractmethod
    async def list_by_tenant(self, tenant_id: str) -> list[User]:
        """List users for a tenant."""

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update a user."""
