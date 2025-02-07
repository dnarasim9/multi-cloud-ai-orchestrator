"""Deployment aggregate root with full state machine."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from orchestrator.domain.events.deployment_events import (
    DeploymentApproved,
    DeploymentCompleted,
    DeploymentFailed,
    DeploymentPlanGenerated,
    DeploymentRollbackCompleted,
    DeploymentRollbackStarted,
    DeploymentStarted,
)
from orchestrator.domain.models.base import AggregateRoot, generate_id, ValueObject
from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceSpec


class DeploymentStatus(str, Enum):
    """Deployment lifecycle states."""

    PENDING = "pending"
    PLANNING = "planning"
    PLANNED = "planned"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class DeploymentStrategy(str, Enum):
    """Deployment strategies."""

    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"


# State machine transitions
VALID_TRANSITIONS: dict[DeploymentStatus, set[DeploymentStatus]] = {
    DeploymentStatus.PENDING: {DeploymentStatus.PLANNING, DeploymentStatus.CANCELLED},
    DeploymentStatus.PLANNING: {DeploymentStatus.PLANNED, DeploymentStatus.FAILED},
    DeploymentStatus.PLANNED: {
        DeploymentStatus.AWAITING_APPROVAL, DeploymentStatus.APPROVED,
        DeploymentStatus.EXECUTING, DeploymentStatus.CANCELLED,
    },
    DeploymentStatus.AWAITING_APPROVAL: {
        DeploymentStatus.APPROVED, DeploymentStatus.CANCELLED,
    },
    DeploymentStatus.APPROVED: {
        DeploymentStatus.EXECUTING, DeploymentStatus.CANCELLED,
    },
    DeploymentStatus.EXECUTING: {
        DeploymentStatus.VERIFYING, DeploymentStatus.FAILED,
        DeploymentStatus.ROLLING_BACK,
    },
    DeploymentStatus.VERIFYING: {
        DeploymentStatus.COMPLETED, DeploymentStatus.FAILED,
        DeploymentStatus.ROLLING_BACK,
    },
    DeploymentStatus.COMPLETED: set(),
    DeploymentStatus.FAILED: {DeploymentStatus.ROLLING_BACK, DeploymentStatus.PENDING},
    DeploymentStatus.ROLLING_BACK: {DeploymentStatus.ROLLED_BACK, DeploymentStatus.FAILED},
    DeploymentStatus.ROLLED_BACK: {DeploymentStatus.PENDING},
    DeploymentStatus.CANCELLED: set(),
}


class DeploymentIntent(ValueObject):
    """The user's deployment intent - what they want deployed."""

    description: str
    target_providers: list[CloudProviderType]
    target_regions: list[str] = Field(default_factory=list)
    resources: list[ResourceSpec] = Field(default_factory=list)
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    auto_approve: bool = False
    rollback_on_failure: bool = True
    environment: str = "staging"
    parameters: dict[str, Any] = Field(default_factory=dict)


class ExecutionStep(ValueObject):
    """A single step in the execution plan."""

    step_id: str = Field(default_factory=generate_id)
    name: str
    description: str
    provider: CloudProviderType
    resource_spec: ResourceSpec
    terraform_action: str  # "create", "update", "destroy"
    dependencies: list[str] = Field(default_factory=list)
    estimated_duration_seconds: int = 60
    idempotency_key: str = Field(default_factory=generate_id)
    retry_count: int = 0
    max_retries: int = 3


class ExecutionPlan(ValueObject):
    """Execution plan generated for a deployment."""

    plan_id: str = Field(default_factory=generate_id)
    steps: list[ExecutionStep] = Field(default_factory=list)
    estimated_total_duration_seconds: int = 0
    risk_assessment: str = "low"
    reasoning: str = ""
    terraform_plan_output: str = ""

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def get_step(self, step_id: str) -> ExecutionStep | None:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_execution_order(self) -> list[list[ExecutionStep]]:
        """Get steps grouped by execution waves (parallelizable groups)."""
        completed: set[str] = set()
        waves: list[list[ExecutionStep]] = []
        remaining = list(self.steps)

        while remaining:
            wave = [
                step for step in remaining
                if all(dep in completed for dep in step.dependencies)
            ]
            if not wave:
                wave = [remaining[0]]
            waves.append(wave)
            for step in wave:
                completed.add(step.step_id)
                remaining.remove(step)

        return waves


class StepResult(ValueObject):
    """Result of executing a single step."""

    step_id: str
    success: bool
    output: str = ""
    error_message: str = ""
    resource_ids: dict[str, str] = Field(default_factory=dict)
    duration_seconds: float = 0.0
    idempotency_key: str = ""
    attempt_number: int = 1


class Deployment(AggregateRoot):
    """Deployment aggregate root - the central domain entity."""

    name: str
    intent: DeploymentIntent
    status: DeploymentStatus = DeploymentStatus.PENDING
    plan: ExecutionPlan | None = None
    step_results: list[StepResult] = Field(default_factory=list)
    initiated_by: str = ""
    tenant_id: str = ""
    error_message: str = ""
    rollback_deployment_id: str | None = None

    def _transition_to(self, new_status: DeploymentStatus) -> None:
        """Validate and execute state transition."""
        valid = VALID_TRANSITIONS.get(self.status, set())
        if new_status not in valid:
            raise InvalidStateTransitionError(
                f"Cannot transition from {self.status.value} to {new_status.value}. "
                f"Valid transitions: {[s.value for s in valid]}"
            )
        self.status = new_status
        self.touch()

    def start_planning(self) -> None:
        """Transition deployment into the planning phase."""
        self._transition_to(DeploymentStatus.PLANNING)

    def set_plan(self, plan: ExecutionPlan) -> None:
        """Attach the generated execution plan to this deployment."""
        self.plan = plan
        self._transition_to(DeploymentStatus.PLANNED)
        self.add_event(DeploymentPlanGenerated(
            deployment_id=self.id,
            plan_id=plan.plan_id,
            step_count=plan.step_count,
            correlation_id=self.id,
        ))
        if self.intent.auto_approve:
            self.approve(approved_by="auto")
        else:
            self._transition_to(DeploymentStatus.AWAITING_APPROVAL)

    def approve(self, approved_by: str) -> None:
        """Approve the deployment for execution."""
        self._transition_to(DeploymentStatus.APPROVED)
        self.add_event(DeploymentApproved(
            deployment_id=self.id,
            approved_by=approved_by,
            correlation_id=self.id,
        ))

    def start_execution(self) -> None:
        """Begin executing the deployment plan."""
        self._transition_to(DeploymentStatus.EXECUTING)
        self.add_event(DeploymentStarted(
            deployment_id=self.id,
            correlation_id=self.id,
        ))

    def record_step_result(self, result: StepResult) -> None:
        """Record the result of an execution step."""
        self.step_results.append(result)
        self.touch()

        if not result.success and self.intent.rollback_on_failure:
            self.fail(f"Step {result.step_id} failed: {result.error_message}")

    def start_verification(self) -> None:
        """Start post-deployment verification."""
        self._transition_to(DeploymentStatus.VERIFYING)

    def complete(self) -> None:
        """Mark deployment as successfully completed."""
        self._transition_to(DeploymentStatus.COMPLETED)
        self.add_event(DeploymentCompleted(
            deployment_id=self.id,
            correlation_id=self.id,
        ))

    def fail(self, error_message: str) -> None:
        """Mark deployment as failed."""
        self.error_message = error_message
        self._transition_to(DeploymentStatus.FAILED)
        self.add_event(DeploymentFailed(
            deployment_id=self.id,
            error_message=error_message,
            correlation_id=self.id,
        ))

    def start_rollback(self) -> None:
        """Initiate deployment rollback."""
        self._transition_to(DeploymentStatus.ROLLING_BACK)
        self.add_event(DeploymentRollbackStarted(
            deployment_id=self.id,
            correlation_id=self.id,
        ))

    def complete_rollback(self) -> None:
        """Mark rollback as complete."""
        self._transition_to(DeploymentStatus.ROLLED_BACK)
        self.add_event(DeploymentRollbackCompleted(
            deployment_id=self.id,
            correlation_id=self.id,
        ))

    def cancel(self) -> None:
        """Cancel the deployment."""
        self._transition_to(DeploymentStatus.CANCELLED)

    @property
    def is_terminal(self) -> bool:
        """Check if deployment is in a terminal state."""
        return self.status in {
            DeploymentStatus.COMPLETED,
            DeploymentStatus.CANCELLED,
            DeploymentStatus.ROLLED_BACK,
        }

    @property
    def progress_percentage(self) -> float:
        """Calculate execution progress."""
        if not self.plan or not self.plan.steps:
            return 0.0
        return (len(self.step_results) / len(self.plan.steps)) * 100


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
