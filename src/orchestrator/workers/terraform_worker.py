"""Terraform execution worker agent."""

from __future__ import annotations

import os
import tempfile
from typing import Any

import structlog

from orchestrator.domain.models.cloud_provider import ResourceSpec
from orchestrator.domain.models.task import Task
from orchestrator.domain.ports.services import TerraformExecutor
from orchestrator.workers.base import HealthCheckMixin, WorkerAgent


logger = structlog.get_logger(__name__)


class TerraformWorkerAgent(WorkerAgent, HealthCheckMixin):
    """Worker agent that executes Terraform operations.

    Handles infrastructure provisioning tasks by generating
    Terraform configurations and executing plan/apply/destroy.
    """

    def __init__(
        self,
        terraform_executor: TerraformExecutor,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._terraform = terraform_executor
        self._work_dir_base = tempfile.mkdtemp(prefix="tf-worker-")

    async def execute(self, task: Task) -> dict[str, Any]:
        """Execute a Terraform task through the standard init → plan → apply lifecycle."""
        resource_spec = ResourceSpec.model_validate(task.input_data.get("resource_spec", {}))
        work_dir = os.path.join(self._work_dir_base, task.deployment_id, task.step_id)

        logger.info(
            "terraform_task_executing",
            task_id=task.id,
            action=task.terraform_action,
            provider=resource_spec.provider.value,
            resource=resource_spec.name,
        )

        await self._terraform.generate_config(resource_spec, work_dir)
        await self._run_phase("init", self._terraform.init(work_dir, resource_spec.provider))
        await self._run_phase("plan", self._terraform.plan(work_dir))
        await self._apply_action(task.terraform_action, work_dir)

        state = await self._terraform.show_state(work_dir)
        return {
            "action": task.terraform_action,
            "resource": resource_spec.name,
            "provider": resource_spec.provider.value,
            "state": state,
            "work_dir": work_dir,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _run_phase(name: str, coro: Any) -> str:
        """Run a Terraform phase and raise on failure."""
        success, output = await coro
        if not success:
            raise TerraformExecutionError(f"{name.capitalize()} failed: {output}")
        return str(output)

    async def _apply_action(self, action: str, work_dir: str) -> None:
        """Execute the apply or destroy phase based on the requested action."""
        if action in ("create", "update"):
            await self._run_phase("apply", self._terraform.apply(work_dir))
        elif action == "destroy":
            await self._run_phase("destroy", self._terraform.destroy(work_dir))


class TerraformExecutionError(Exception):
    """Raised when Terraform execution fails."""
