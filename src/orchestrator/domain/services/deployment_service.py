"""Domain service for deployment orchestration logic."""

from __future__ import annotations

from typing import Any

import structlog

from orchestrator.domain.models.base import AggregateRoot
from orchestrator.domain.models.deployment import (
    Deployment,
    DeploymentIntent,
    StepResult,
)
from orchestrator.domain.models.task import Task, TaskStatus
from orchestrator.domain.ports.repositories import DeploymentRepository, TaskRepository
from orchestrator.domain.ports.services import (
    DistributedLock,
    EventPublisher,
    PlanningEngine,
)


logger = structlog.get_logger(__name__)


class DeploymentDomainService:
    """Domain service coordinating deployment lifecycle operations.

    This service encapsulates complex domain logic that spans multiple
    aggregates (Deployment + Task) and requires coordination with
    infrastructure services through ports.
    """

    def __init__(
        self,
        deployment_repo: DeploymentRepository,
        task_repo: TaskRepository,
        planning_engine: PlanningEngine,
        event_publisher: EventPublisher,
        lock_service: DistributedLock,
    ) -> None:
        self._deployment_repo = deployment_repo
        self._task_repo = task_repo
        self._planning_engine = planning_engine
        self._event_publisher = event_publisher
        self._lock_service = lock_service

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _publish_events(self, aggregate: AggregateRoot) -> None:
        """Collect and publish all pending domain events from an aggregate."""
        for event in aggregate.collect_events():
            await self._event_publisher.publish(
                event.event_type, event.model_dump()
            )

    # ------------------------------------------------------------------
    # Lifecycle operations
    # ------------------------------------------------------------------

    async def create_deployment(
        self, intent: DeploymentIntent, initiated_by: str, tenant_id: str
    ) -> Deployment:
        """Create a new deployment from intent."""
        deployment = Deployment(
            name=f"deploy-{intent.environment}-{intent.target_providers[0].value}",
            intent=intent,
            initiated_by=initiated_by,
            tenant_id=tenant_id,
        )
        deployment = await self._deployment_repo.save(deployment)

        await self._event_publisher.publish(
            "deployment.created",
            {"deployment_id": deployment.id, "tenant_id": tenant_id},
        )

        logger.info(
            "deployment_created",
            deployment_id=deployment.id,
            environment=intent.environment,
            providers=[p.value for p in intent.target_providers],
        )
        return deployment

    async def plan_deployment(self, deployment_id: str) -> Deployment:
        """Generate an execution plan for the given deployment."""
        lock_key = f"deployment:{deployment_id}:planning"
        acquired = await self._lock_service.acquire(lock_key, ttl_seconds=120)
        if not acquired:
            raise DeploymentLockError(
                f"Could not acquire planning lock for deployment {deployment_id}"
            )

        try:
            deployment = await self._deployment_repo.get_by_id(deployment_id)
            if deployment is None:
                raise DeploymentNotFoundError(f"Deployment {deployment_id} not found")

            deployment.start_planning()
            plan = await self._planning_engine.generate_plan(deployment.intent)
            deployment.set_plan(plan)
            deployment = await self._deployment_repo.update(deployment)

            await self._publish_events(deployment)

            logger.info(
                "deployment_planned",
                deployment_id=deployment_id,
                step_count=plan.step_count,
            )
            return deployment

        finally:
            await self._lock_service.release(lock_key)

    async def execute_deployment(self, deployment_id: str) -> list[Task]:
        """Create tasks from execution plan and begin execution."""
        deployment = await self._deployment_repo.get_by_id(deployment_id)
        if deployment is None:
            raise DeploymentNotFoundError(f"Deployment {deployment_id} not found")

        if deployment.plan is None:
            raise DeploymentPlanMissingError(
                f"Deployment {deployment_id} has no execution plan"
            )

        plan = deployment.plan  # captured before update to preserve narrowing
        deployment.start_execution()
        deployment = await self._deployment_repo.update(deployment)

        tasks: list[Task] = []
        for step in plan.steps:
            task = Task(
                deployment_id=deployment_id,
                step_id=step.step_id,
                name=step.name,
                description=step.description,
                provider=step.provider,
                terraform_action=step.terraform_action,
                idempotency_key=step.idempotency_key,
                timeout_seconds=step.estimated_duration_seconds * 2,
                input_data={
                    "resource_spec": step.resource_spec.model_dump(),
                    "dependencies": step.dependencies,
                },
            )
            task.enqueue()
            task = await self._task_repo.save(task)
            tasks.append(task)

        await self._publish_events(deployment)

        logger.info(
            "deployment_execution_started",
            deployment_id=deployment_id,
            task_count=len(tasks),
        )
        return tasks

    async def handle_task_completion(
        self,
        task_id: str,
        success: bool,
        output: dict[str, Any] | None = None,
        error: str = "",
    ) -> None:
        """Handle task completion and check if deployment is finished."""
        task = await self._task_repo.get_by_id(task_id)
        if task is None:
            return

        if success:
            task.succeed(output)
        else:
            task.fail(error)

        await self._task_repo.update(task)

        deployment = await self._deployment_repo.get_by_id(task.deployment_id)
        if deployment is None:
            return

        step_result = StepResult(
            step_id=task.step_id,
            success=success,
            output=str(output) if output else "",
            error_message=error,
            idempotency_key=task.idempotency_key,
            attempt_number=task.attempt_number,
        )
        deployment.record_step_result(step_result)

        all_tasks = await self._task_repo.list_by_deployment(task.deployment_id)
        all_complete = all(t.is_terminal or t.status == TaskStatus.SUCCEEDED for t in all_tasks)
        any_failed = any(t.status == TaskStatus.FAILED for t in all_tasks)

        if all_complete and not any_failed:
            deployment.start_verification()
        elif any_failed and deployment.intent.rollback_on_failure:
            deployment.start_rollback()

        await self._deployment_repo.update(deployment)
        await self._publish_events(deployment)

    async def approve_deployment(self, deployment_id: str, approved_by: str) -> Deployment:
        """Approve a deployment for execution."""
        deployment = await self._deployment_repo.get_by_id(deployment_id)
        if deployment is None:
            raise DeploymentNotFoundError(f"Deployment {deployment_id} not found")

        deployment.approve(approved_by=approved_by)
        deployment = await self._deployment_repo.update(deployment)
        await self._publish_events(deployment)
        return deployment

    async def rollback_deployment(self, deployment_id: str) -> Deployment:
        """Initiate rollback of a deployment."""
        deployment = await self._deployment_repo.get_by_id(deployment_id)
        if deployment is None:
            raise DeploymentNotFoundError(f"Deployment {deployment_id} not found")

        deployment.start_rollback()
        deployment = await self._deployment_repo.update(deployment)
        await self._publish_events(deployment)
        return deployment


class DeploymentNotFoundError(Exception):
    """Raised when a deployment is not found."""


class DeploymentPlanMissingError(Exception):
    """Raised when a deployment has no execution plan."""


class DeploymentLockError(Exception):
    """Raised when a deployment lock cannot be acquired."""
