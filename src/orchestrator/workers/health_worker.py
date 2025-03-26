"""Health check worker agent."""

from __future__ import annotations

from typing import Any

import structlog

from orchestrator.domain.models.task import Task
from orchestrator.workers.base import WorkerAgent


logger = structlog.get_logger(__name__)


class SimulatedHealthChecker:
    """Simulated health checker for development."""

    async def check_resource(
        self, _provider: str, resource_id: str
    ) -> tuple[bool, str]:
        return True, f"Resource {resource_id} is healthy"

    async def check_deployment(self, deployment_id: str) -> dict[str, Any]:
        return {"deployment_id": deployment_id, "status": "healthy", "checks": {}}


class HealthCheckWorkerAgent(WorkerAgent):
    """Worker agent that performs health checks on deployed resources."""

    def __init__(
        self,
        health_checker: SimulatedHealthChecker | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._health_checker = health_checker or SimulatedHealthChecker()

    async def execute(self, task: Task) -> dict[str, Any]:
        """Execute health check task."""
        resource_ids = task.input_data.get("resource_ids", [])
        provider = task.input_data.get("provider", "aws")

        results: dict[str, Any] = {}
        all_healthy = True

        for resource_id in resource_ids:
            healthy, message = await self._health_checker.check_resource(
                provider, resource_id
            )
            results[resource_id] = {"healthy": healthy, "message": message}
            if not healthy:
                all_healthy = False

        logger.info(
            "health_check_completed",
            task_id=task.id,
            all_healthy=all_healthy,
            checked_count=len(resource_ids),
        )

        return {
            "all_healthy": all_healthy,
            "results": results,
        }
