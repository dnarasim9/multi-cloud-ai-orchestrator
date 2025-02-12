"""Deployment domain events."""

from __future__ import annotations

from orchestrator.domain.models.base import DomainEvent


class DeploymentCreated(DomainEvent):
    """Emitted when a deployment is created."""

    deployment_id: str
    event_type: str = "deployment.created"


class DeploymentPlanGenerated(DomainEvent):
    """Emitted when an execution plan is generated."""

    deployment_id: str
    plan_id: str
    step_count: int
    event_type: str = "deployment.plan_generated"


class DeploymentApproved(DomainEvent):
    """Emitted when a deployment is approved."""

    deployment_id: str
    approved_by: str
    event_type: str = "deployment.approved"


class DeploymentStarted(DomainEvent):
    """Emitted when deployment execution starts."""

    deployment_id: str
    event_type: str = "deployment.started"


class DeploymentCompleted(DomainEvent):
    """Emitted when deployment completes successfully."""

    deployment_id: str
    event_type: str = "deployment.completed"


class DeploymentFailed(DomainEvent):
    """Emitted when deployment fails."""

    deployment_id: str
    error_message: str
    event_type: str = "deployment.failed"


class DeploymentRollbackStarted(DomainEvent):
    """Emitted when rollback starts."""

    deployment_id: str
    event_type: str = "deployment.rollback_started"


class DeploymentRollbackCompleted(DomainEvent):
    """Emitted when rollback completes."""

    deployment_id: str
    event_type: str = "deployment.rollback_completed"
