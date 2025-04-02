"""Unit tests for terraform worker agent."""

from __future__ import annotations

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceSpec, ResourceType
from orchestrator.domain.models.task import Task
from orchestrator.infrastructure.terraform.executor import SimulatedTerraformExecutor
from orchestrator.workers.terraform_worker import TerraformWorkerAgent


class TestTerraformWorkerAgent:
    @pytest.mark.asyncio
    async def test_execute_create(self) -> None:
        executor = SimulatedTerraformExecutor()
        worker = TerraformWorkerAgent(
            terraform_executor=executor,
            worker_id="tf-worker-1",
        )
        task = Task(
            deployment_id="d1",
            step_id="s1",
            name="create-instance",
            provider=CloudProviderType.AWS,
            terraform_action="create",
            input_data={
                "resource_spec": ResourceSpec(
                    resource_type=ResourceType.COMPUTE,
                    provider=CloudProviderType.AWS,
                    region="us-east-1",
                    name="test-instance",
                    properties={"instance_type": "t3.medium"},
                ).model_dump(),
            },
        )
        result = await worker.execute(task)
        assert result["action"] == "create"
        assert result["provider"] == "aws"
        assert result["resource"] == "test-instance"

    @pytest.mark.asyncio
    async def test_execute_destroy(self) -> None:
        executor = SimulatedTerraformExecutor()
        worker = TerraformWorkerAgent(
            terraform_executor=executor,
            worker_id="tf-worker-1",
        )
        task = Task(
            deployment_id="d1",
            step_id="s1",
            name="destroy-instance",
            provider=CloudProviderType.AWS,
            terraform_action="destroy",
            input_data={
                "resource_spec": ResourceSpec(
                    resource_type=ResourceType.COMPUTE,
                    provider=CloudProviderType.AWS,
                    region="us-east-1",
                    name="test-instance",
                ).model_dump(),
            },
        )
        result = await worker.execute(task)
        assert result["action"] == "destroy"

    @pytest.mark.asyncio
    async def test_worker_health(self) -> None:
        executor = SimulatedTerraformExecutor()
        worker = TerraformWorkerAgent(
            terraform_executor=executor,
            worker_id="tf-worker-1",
        )
        health = worker.get_health()
        assert health["worker_id"] == "tf-worker-1"
        assert health["active_tasks"] == 0
        assert health["running"] is False
