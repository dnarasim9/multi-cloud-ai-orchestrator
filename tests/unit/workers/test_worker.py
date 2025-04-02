"""Unit tests for worker agents."""

from __future__ import annotations

from typing import Any

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType
from orchestrator.domain.models.task import Task, TaskStatus
from orchestrator.infrastructure.messaging.event_publisher import InMemoryEventPublisher
from orchestrator.infrastructure.persistence.repositories.in_memory import InMemoryTaskRepository
from orchestrator.workers.base import WorkerAgent


class SimpleWorker(WorkerAgent):
    """Simple worker for testing."""

    def __init__(
        self, result: dict | None = None, should_fail: bool = False, **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._result = result or {"status": "ok"}
        self._should_fail = should_fail
        self.executed_tasks: list[str] = []

    async def execute(self, task: Task) -> dict[str, Any]:
        self.executed_tasks.append(task.id)
        if self._should_fail:
            raise RuntimeError("Simulated failure")
        return self._result


class TestWorkerAgent:
    @pytest.mark.asyncio
    async def test_worker_has_id(self) -> None:
        worker = SimpleWorker()
        assert worker.worker_id.startswith("worker-")

    @pytest.mark.asyncio
    async def test_custom_worker_id(self) -> None:
        worker = SimpleWorker(worker_id="my-worker")
        assert worker.worker_id == "my-worker"

    @pytest.mark.asyncio
    async def test_execute_task_success(self) -> None:
        task_repo = InMemoryTaskRepository()
        event_pub = InMemoryEventPublisher()

        task = Task(
            deployment_id="d-1",
            step_id="s-1",
            name="test-task",
            provider=CloudProviderType.AWS,
            terraform_action="create",
        )
        task.enqueue()
        await task_repo.save(task)

        worker = SimpleWorker(
            task_repo=task_repo,
            event_publisher=event_pub,
            worker_id="test-worker",
        )

        acquired = await task_repo.acquire_next("test-worker")
        assert acquired is not None
        await worker._execute_task_lifecycle(acquired)

        updated = await task_repo.get_by_id(task.id)
        assert updated.status == TaskStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_execute_task_failure(self) -> None:
        task_repo = InMemoryTaskRepository()

        task = Task(
            deployment_id="d-1",
            step_id="s-1",
            name="fail-task",
            provider=CloudProviderType.AWS,
            terraform_action="create",
        )
        task.enqueue()
        await task_repo.save(task)

        worker = SimpleWorker(
            should_fail=True,
            task_repo=task_repo,
            worker_id="test-worker",
        )

        acquired = await task_repo.acquire_next("test-worker")
        await worker._execute_task_lifecycle(acquired)

        updated = await task_repo.get_by_id(task.id)
        assert updated.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_active_task_tracking(self) -> None:
        worker = SimpleWorker(worker_id="test-worker")
        assert worker.active_task_count == 0
