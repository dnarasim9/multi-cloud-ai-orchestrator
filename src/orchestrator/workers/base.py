"""Base worker agent implementation."""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Any

import structlog

from orchestrator.domain.models.task import Task
from orchestrator.domain.ports.repositories import TaskRepository
from orchestrator.domain.ports.services import DistributedLock, EventPublisher


logger = structlog.get_logger(__name__)


class WorkerAgent(ABC):
    """Base class for worker agents that process deployment tasks.

    Implements the Template Method pattern for task execution lifecycle.
    """

    def __init__(
        self,
        worker_id: str | None = None,
        task_repo: TaskRepository | None = None,
        lock_service: DistributedLock | None = None,
        event_publisher: EventPublisher | None = None,
        poll_interval: float = 2.0,
        max_concurrent: int = 5,
    ) -> None:
        self._worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._task_repo = task_repo
        self._lock_service = lock_service
        self._event_publisher = event_publisher
        self._poll_interval = poll_interval
        self._max_concurrent = max_concurrent
        self._running = False
        self._active_tasks: set[str] = set()
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._semaphore = asyncio.Semaphore(max_concurrent)

    @property
    def worker_id(self) -> str:
        return self._worker_id

    @property
    def active_task_count(self) -> int:
        return len(self._active_tasks)

    async def start(self) -> None:
        """Start the worker agent polling loop."""
        self._running = True
        logger.info("worker_started", worker_id=self._worker_id)

        while self._running:
            try:
                await self._poll_for_tasks()
            except Exception as e:
                logger.exception("worker_poll_error", worker_id=self._worker_id, error=str(e))
            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        """Gracefully stop the worker agent."""
        self._running = False
        logger.info(
            "worker_stopping",
            worker_id=self._worker_id,
            active_tasks=self.active_task_count,
        )

        # Wait for active tasks to complete
        while self._active_tasks:
            await asyncio.sleep(0.5)

        logger.info("worker_stopped", worker_id=self._worker_id)

    async def _poll_for_tasks(self) -> None:
        """Poll for and acquire new tasks."""
        if self._task_repo is None:
            return

        if self.active_task_count >= self._max_concurrent:
            return

        task = await self._task_repo.acquire_next(self._worker_id)
        if task is not None:
            background_task = asyncio.create_task(self._execute_task_lifecycle(task))
            self._background_tasks.add(background_task)
            background_task.add_done_callback(self._background_tasks.discard)

    async def _execute_task_lifecycle(self, task: Task) -> None:
        """Execute the full task lifecycle with error handling."""
        self._active_tasks.add(task.id)

        try:
            async with self._semaphore:
                task.start()
                if self._task_repo:
                    await self._task_repo.update(task)

                logger.info(
                    "task_execution_started",
                    task_id=task.id,
                    worker_id=self._worker_id,
                    deployment_id=task.deployment_id,
                )

                # Execute with timeout
                try:
                    result = await asyncio.wait_for(
                        self.execute(task),
                        timeout=task.timeout_seconds,
                    )
                    task.succeed(result)
                    logger.info("task_succeeded", task_id=task.id)
                except asyncio.TimeoutError:
                    task.timeout()
                    logger.warning("task_timed_out", task_id=task.id)
                except Exception as e:
                    task.fail(str(e))
                    logger.exception("task_failed", task_id=task.id, error=str(e))

                if self._task_repo:
                    await self._task_repo.update(task)

                if self._event_publisher:
                    await self._event_publisher.publish(
                        f"task.{task.status.value}",
                        {
                            "task_id": task.id,
                            "deployment_id": task.deployment_id,
                            "worker_id": self._worker_id,
                            "status": task.status.value,
                        },
                    )

        finally:
            self._active_tasks.discard(task.id)

    @abstractmethod
    async def execute(self, task: Task) -> dict[str, Any]:
        """Execute the task. Subclasses implement specific logic."""


class HealthCheckMixin:
    """Mixin for worker health checking capability.

    Intended to be used alongside :class:`WorkerAgent` in a cooperative
    multiple-inheritance class hierarchy.
    """

    def get_health(self: WorkerAgent) -> dict[str, Any]:  # type: ignore[misc]
        """Return a health snapshot of the worker."""
        return {
            "worker_id": self.worker_id,
            "active_tasks": self.active_task_count,
            "running": self._running,
            "max_concurrent": self._max_concurrent,
        }
