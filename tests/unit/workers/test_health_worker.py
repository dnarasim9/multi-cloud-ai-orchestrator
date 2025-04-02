"""Unit tests for health check worker agent."""

from __future__ import annotations

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType
from orchestrator.domain.models.task import Task
from orchestrator.workers.health_worker import HealthCheckWorkerAgent, SimulatedHealthChecker


class TestHealthCheckWorkerAgent:
    @pytest.mark.asyncio
    async def test_execute_health_check(self) -> None:
        worker = HealthCheckWorkerAgent(worker_id="health-1")
        task = Task(
            deployment_id="d1",
            step_id="s1",
            name="health-check",
            provider=CloudProviderType.AWS,
            terraform_action="check",
            input_data={
                "resource_ids": ["res-1", "res-2"],
                "provider": "aws",
            },
        )
        result = await worker.execute(task)
        assert result["all_healthy"] is True
        assert "res-1" in result["results"]
        assert "res-2" in result["results"]

    @pytest.mark.asyncio
    async def test_execute_empty_resources(self) -> None:
        worker = HealthCheckWorkerAgent(worker_id="health-1")
        task = Task(
            deployment_id="d1",
            step_id="s1",
            name="health-check",
            provider=CloudProviderType.AWS,
            terraform_action="check",
            input_data={"resource_ids": [], "provider": "aws"},
        )
        result = await worker.execute(task)
        assert result["all_healthy"] is True
        assert len(result["results"]) == 0


class TestSimulatedHealthChecker:
    @pytest.mark.asyncio
    async def test_check_resource(self) -> None:
        checker = SimulatedHealthChecker()
        healthy, msg = await checker.check_resource("aws", "res-1")
        assert healthy is True
        assert "res-1" in msg

    @pytest.mark.asyncio
    async def test_check_deployment(self) -> None:
        checker = SimulatedHealthChecker()
        result = await checker.check_deployment("d-1")
        assert result["status"] == "healthy"
