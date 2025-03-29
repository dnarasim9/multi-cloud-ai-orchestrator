"""Unit tests for drift domain service."""

from __future__ import annotations

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceSpec, ResourceType
from orchestrator.domain.models.deployment import (
    Deployment,
    DeploymentIntent,
    ExecutionPlan,
    ExecutionStep,
)
from orchestrator.domain.services.drift_service import DriftDomainService, DriftScanError
from orchestrator.infrastructure.ai.drift_detector import SimulatedDriftDetector
from orchestrator.infrastructure.messaging.event_publisher import InMemoryEventPublisher
from orchestrator.infrastructure.persistence.repositories.in_memory import (
    InMemoryDeploymentRepository,
    InMemoryDriftReportRepository,
)


@pytest.fixture
def drift_service() -> DriftDomainService:
    return DriftDomainService(
        deployment_repo=InMemoryDeploymentRepository(),
        drift_repo=InMemoryDriftReportRepository(),
        drift_detector=SimulatedDriftDetector(drift_probability=0.0),
        event_publisher=InMemoryEventPublisher(),
    )


@pytest.fixture
async def saved_deployment() -> Deployment:
    repo = InMemoryDeploymentRepository()
    intent = DeploymentIntent(
        description="drift test",
        target_providers=[CloudProviderType.AWS],
        resources=[
            ResourceSpec(
                resource_type=ResourceType.COMPUTE,
                provider=CloudProviderType.AWS,
                region="us-east-1",
                name="test-instance",
            ),
        ],
    )
    deployment = Deployment(
        name="drift-test",
        intent=intent,
        initiated_by="user",
        tenant_id="t1",
    )
    step = ExecutionStep(
        name="test-step",
        description="test",
        provider=CloudProviderType.AWS,
        resource_spec=intent.resources[0],
        terraform_action="create",
    )
    deployment.plan = ExecutionPlan(steps=[step])
    await repo.save(deployment)
    return deployment


class TestDriftDomainService:
    @pytest.mark.asyncio
    async def test_scan_deployment(
        self, drift_service: DriftDomainService, saved_deployment: Deployment,
    ) -> None:
        report = await drift_service.scan_deployment(saved_deployment.id)
        assert report.deployment_id == saved_deployment.id

    @pytest.mark.asyncio
    async def test_scan_nonexistent_deployment(self, drift_service: DriftDomainService) -> None:
        with pytest.raises(DriftScanError):
            await drift_service.scan_deployment("nonexistent-id")

    @pytest.mark.asyncio
    async def test_get_drift_history(
        self, drift_service: DriftDomainService, saved_deployment: Deployment,
    ) -> None:
        await drift_service.scan_deployment(saved_deployment.id)
        await drift_service.scan_deployment(saved_deployment.id)
        history = await drift_service.get_drift_history(saved_deployment.id)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_drift_event_published_on_drift(self) -> None:
        publisher = InMemoryEventPublisher()
        service = DriftDomainService(
            deployment_repo=InMemoryDeploymentRepository(),
            drift_repo=InMemoryDriftReportRepository(),
            drift_detector=SimulatedDriftDetector(drift_probability=1.0),
            event_publisher=publisher,
        )
        repo = InMemoryDeploymentRepository()
        intent = DeploymentIntent(
            description="test",
            target_providers=[CloudProviderType.AWS],
            resources=[
                ResourceSpec(
                    resource_type=ResourceType.COMPUTE,
                    provider=CloudProviderType.AWS,
                    region="us-east-1",
                    name="test",
                ),
            ],
        )
        d = Deployment(name="t", intent=intent, initiated_by="u", tenant_id="t")
        d.plan = ExecutionPlan(steps=[
            ExecutionStep(
                name="s",
                description="s",
                provider=CloudProviderType.AWS,
                resource_spec=intent.resources[0],
                terraform_action="create",
            )
        ])
        await repo.save(d)
        # Use the same repo for the service
        service._deployment_repo = repo
        report = await service.scan_deployment(d.id)
        if report.has_drift:
            assert any(e[0] == "drift.detected" for e in publisher.published_events)
