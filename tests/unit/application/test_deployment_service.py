"""Unit tests for deployment domain service."""

from __future__ import annotations

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceSpec, ResourceType
from orchestrator.domain.models.deployment import DeploymentIntent, DeploymentStatus
from orchestrator.domain.services.deployment_service import (
    DeploymentDomainService,
    DeploymentNotFoundError,
)
from orchestrator.infrastructure.ai.planning_engine import RuleBasedPlanningEngine
from orchestrator.infrastructure.messaging.event_publisher import InMemoryEventPublisher
from orchestrator.infrastructure.persistence.repositories.in_memory import (
    InMemoryDeploymentRepository,
    InMemoryTaskRepository,
)


class FakeLock:
    """Fake distributed lock for testing."""

    async def acquire(self, resource_id: str, ttl_seconds: int = 30) -> bool:
        return True

    async def release(self, resource_id: str) -> bool:
        return True

    async def extend(self, resource_id: str, ttl_seconds: int = 30) -> bool:
        return True

    async def is_locked(self, resource_id: str) -> bool:
        return False


@pytest.fixture
def service() -> DeploymentDomainService:
    return DeploymentDomainService(
        deployment_repo=InMemoryDeploymentRepository(),
        task_repo=InMemoryTaskRepository(),
        planning_engine=RuleBasedPlanningEngine(),
        event_publisher=InMemoryEventPublisher(),
        lock_service=FakeLock(),  # type: ignore[arg-type]
    )


@pytest.fixture
def intent() -> DeploymentIntent:
    return DeploymentIntent(
        description="Service test",
        target_providers=[CloudProviderType.AWS],
        target_regions=["us-east-1"],
        resources=[
            ResourceSpec(
                resource_type=ResourceType.COMPUTE,
                provider=CloudProviderType.AWS,
                region="us-east-1",
                name="test-instance",
            ),
        ],
    )


class TestDeploymentDomainService:
    @pytest.mark.asyncio
    async def test_create_deployment(
        self, service: DeploymentDomainService, intent: DeploymentIntent
    ) -> None:
        deployment = await service.create_deployment(intent, "user-1", "tenant-1")
        assert deployment.status == DeploymentStatus.PENDING
        assert deployment.initiated_by == "user-1"

    @pytest.mark.asyncio
    async def test_plan_deployment(
        self, service: DeploymentDomainService, intent: DeploymentIntent
    ) -> None:
        deployment = await service.create_deployment(intent, "user-1", "tenant-1")
        planned = await service.plan_deployment(deployment.id)
        assert planned.plan is not None
        assert planned.plan.step_count > 0

    @pytest.mark.asyncio
    async def test_plan_not_found(
        self, service: DeploymentDomainService
    ) -> None:
        with pytest.raises(DeploymentNotFoundError):
            await service.plan_deployment("nonexistent")

    @pytest.mark.asyncio
    async def test_approve_deployment(
        self, service: DeploymentDomainService, intent: DeploymentIntent
    ) -> None:
        deployment = await service.create_deployment(intent, "user-1", "tenant-1")
        await service.plan_deployment(deployment.id)
        approved = await service.approve_deployment(deployment.id, "admin")
        assert approved.status == DeploymentStatus.APPROVED

    @pytest.mark.asyncio
    async def test_execute_deployment(
        self, service: DeploymentDomainService, intent: DeploymentIntent
    ) -> None:
        deployment = await service.create_deployment(intent, "user-1", "tenant-1")
        await service.plan_deployment(deployment.id)
        await service.approve_deployment(deployment.id, "admin")
        tasks = await service.execute_deployment(deployment.id)
        assert len(tasks) > 0

    @pytest.mark.asyncio
    async def test_execute_without_plan_raises(
        self, service: DeploymentDomainService, intent: DeploymentIntent
    ) -> None:
        deployment = await service.create_deployment(intent, "user-1", "tenant-1")
        with pytest.raises(Exception):  # noqa: B017
            await service.execute_deployment(deployment.id)

    @pytest.mark.asyncio
    async def test_rollback_deployment(
        self, service: DeploymentDomainService, intent: DeploymentIntent
    ) -> None:
        deployment = await service.create_deployment(intent, "user-1", "tenant-1")
        await service.plan_deployment(deployment.id)
        await service.approve_deployment(deployment.id, "admin")
        await service.execute_deployment(deployment.id)
        # Force fail to enable rollback
        dep = await service._deployment_repo.get_by_id(deployment.id)
        dep.fail("Test failure")
        await service._deployment_repo.update(dep)
        rolled = await service.rollback_deployment(deployment.id)
        assert rolled.status == DeploymentStatus.ROLLING_BACK
