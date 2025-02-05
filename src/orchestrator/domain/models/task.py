"""Task domain model for individual execution tasks."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from orchestrator.domain.models.base import AggregateRoot, generate_id, utc_now
from orchestrator.domain.models.cloud_provider import CloudProviderType


class TaskStatus(str, Enum):
    """Task execution states."""

    PENDING = "pending"
    QUEUED = "queued"
    ACQUIRED = "acquired"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


TASK_VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {TaskStatus.ACQUIRED, TaskStatus.CANCELLED, TaskStatus.TIMED_OUT},
    TaskStatus.ACQUIRED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.TIMED_OUT},
    TaskStatus.SUCCEEDED: set(),
    TaskStatus.FAILED: {TaskStatus.RETRYING, TaskStatus.CANCELLED},
    TaskStatus.RETRYING: {TaskStatus.QUEUED},
    TaskStatus.CANCELLED: set(),
    TaskStatus.TIMED_OUT: {TaskStatus.RETRYING, TaskStatus.CANCELLED, TaskStatus.FAILED},
}


class Task(AggregateRoot):
    """Individual execution task assigned to a worker agent."""

    deployment_id: str
    step_id: str
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    provider: CloudProviderType = CloudProviderType.AWS
    terraform_action: str = "apply"
    worker_id: str | None = None
    idempotency_key: str = Field(default_factory=generate_id)
    attempt_number: int = 1
    max_attempts: int = 3
    timeout_seconds: int = 300
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str = ""
    started_at: str | None = None
    completed_at: str | None = None

    def _transition_to(self, new_status: TaskStatus) -> None:
        valid = TASK_VALID_TRANSITIONS.get(self.status, set())
        if new_status not in valid:
            raise InvalidTaskTransitionError(
                f"Task cannot transition from {self.status.value} to {new_status.value}"
            )
        self.status = new_status
        self.touch()

    def enqueue(self) -> None:
        self._transition_to(TaskStatus.QUEUED)

    def acquire(self, worker_id: str) -> None:
        self._transition_to(TaskStatus.ACQUIRED)
        self.worker_id = worker_id

    def start(self) -> None:
        self._transition_to(TaskStatus.RUNNING)
        self.started_at = utc_now().isoformat()

    def succeed(self, output: dict[str, Any] | None = None) -> None:
        if output:
            self.output_data = output
        self._transition_to(TaskStatus.SUCCEEDED)
        self.completed_at = utc_now().isoformat()

    def fail(self, error_message: str) -> None:
        self.error_message = error_message
        self._transition_to(TaskStatus.FAILED)
        self.completed_at = utc_now().isoformat()

    def retry(self) -> None:
        if self.attempt_number >= self.max_attempts:
            raise MaxRetriesExceededError(
                f"Task {self.id} has exceeded max retries ({self.max_attempts})"
            )
        self._transition_to(TaskStatus.RETRYING)
        self.attempt_number += 1
        self.worker_id = None
        self.error_message = ""
        self._transition_to(TaskStatus.QUEUED)

    def timeout(self) -> None:
        self._transition_to(TaskStatus.TIMED_OUT)
        self.completed_at = utc_now().isoformat()

    def cancel(self) -> None:
        self._transition_to(TaskStatus.CANCELLED)
        self.completed_at = utc_now().isoformat()

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            TaskStatus.SUCCEEDED,
            TaskStatus.CANCELLED,
        }

    @property
    def can_retry(self) -> bool:
        return (
            self.status in {TaskStatus.FAILED, TaskStatus.TIMED_OUT}
            and self.attempt_number < self.max_attempts
        )


class InvalidTaskTransitionError(Exception):
    """Raised when an invalid task state transition is attempted."""


class MaxRetriesExceededError(Exception):
    """Raised when max retries are exceeded."""
