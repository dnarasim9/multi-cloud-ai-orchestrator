"""Unit tests for task domain model."""

from __future__ import annotations

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType
from orchestrator.domain.models.task import (
    InvalidTaskTransitionError,
    MaxRetriesExceededError,
    Task,
    TASK_VALID_TRANSITIONS,
    TaskStatus,
)


@pytest.fixture
def sample_task() -> Task:
    return Task(
        deployment_id="deploy-123",
        step_id="step-456",
        name="create-instance",
        provider=CloudProviderType.AWS,
        terraform_action="create",
        max_attempts=3,
        timeout_seconds=120,
    )


class TestTaskStateMachine:
    def test_initial_status_pending(self, sample_task: Task) -> None:
        assert sample_task.status == TaskStatus.PENDING

    def test_enqueue(self, sample_task: Task) -> None:
        sample_task.enqueue()
        assert sample_task.status == TaskStatus.QUEUED

    def test_acquire(self, sample_task: Task) -> None:
        sample_task.enqueue()
        sample_task.acquire("worker-1")
        assert sample_task.status == TaskStatus.ACQUIRED
        assert sample_task.worker_id == "worker-1"

    def test_start(self, sample_task: Task) -> None:
        sample_task.enqueue()
        sample_task.acquire("worker-1")
        sample_task.start()
        assert sample_task.status == TaskStatus.RUNNING
        assert sample_task.started_at is not None

    def test_succeed(self, sample_task: Task) -> None:
        sample_task.enqueue()
        sample_task.acquire("worker-1")
        sample_task.start()
        sample_task.succeed({"result": "ok"})
        assert sample_task.status == TaskStatus.SUCCEEDED
        assert sample_task.output_data == {"result": "ok"}
        assert sample_task.completed_at is not None

    def test_fail(self, sample_task: Task) -> None:
        sample_task.enqueue()
        sample_task.acquire("worker-1")
        sample_task.start()
        sample_task.fail("Something went wrong")
        assert sample_task.status == TaskStatus.FAILED
        assert sample_task.error_message == "Something went wrong"

    def test_retry_increments_attempt(self, sample_task: Task) -> None:
        sample_task.enqueue()
        sample_task.acquire("worker-1")
        sample_task.start()
        sample_task.fail("Error")
        initial_attempt = sample_task.attempt_number
        sample_task.retry()
        assert sample_task.attempt_number == initial_attempt + 1
        assert sample_task.status == TaskStatus.QUEUED
        assert sample_task.worker_id is None

    def test_max_retries_exceeded(self, sample_task: Task) -> None:
        for i in range(3):
            if i == 0:
                sample_task.enqueue()
            sample_task.acquire(f"worker-{i}")
            sample_task.start()
            sample_task.fail("Error")
            if i < 2:
                sample_task.retry()

        with pytest.raises(MaxRetriesExceededError):
            sample_task.retry()

    def test_timeout(self, sample_task: Task) -> None:
        sample_task.enqueue()
        sample_task.acquire("worker-1")
        sample_task.start()
        sample_task.timeout()
        assert sample_task.status == TaskStatus.TIMED_OUT

    def test_cancel(self, sample_task: Task) -> None:
        sample_task.enqueue()
        sample_task.cancel()
        assert sample_task.status == TaskStatus.CANCELLED
        assert sample_task.is_terminal

    def test_invalid_transition(self, sample_task: Task) -> None:
        with pytest.raises(InvalidTaskTransitionError):
            sample_task.start()

    def test_can_retry_property(self, sample_task: Task) -> None:
        sample_task.enqueue()
        sample_task.acquire("worker-1")
        sample_task.start()
        sample_task.fail("Error")
        assert sample_task.can_retry is True

    def test_all_transitions_defined(self) -> None:
        for status in TaskStatus:
            assert status in TASK_VALID_TRANSITIONS
