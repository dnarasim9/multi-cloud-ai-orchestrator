"""Unit tests for AI planning engine."""

from __future__ import annotations

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceSpec, ResourceType
from orchestrator.domain.models.deployment import DeploymentIntent
from orchestrator.infrastructure.ai.planning_engine import RuleBasedPlanningEngine


EXPECTED_RESOURCE_COUNT = 2


@pytest.fixture
def engine() -> RuleBasedPlanningEngine:
    return RuleBasedPlanningEngine()


class TestPlanningEngine:
    @pytest.mark.asyncio
    async def test_generate_plan_with_resources(
        self, engine: RuleBasedPlanningEngine
    ) -> None:
        intent = DeploymentIntent(
            description="Test deployment",
            target_providers=[CloudProviderType.AWS],
            resources=[
                ResourceSpec(
                    resource_type=ResourceType.NETWORK,
                    provider=CloudProviderType.AWS,
                    region="us-east-1",
                    name="test-vpc",
                ),
                ResourceSpec(
                    resource_type=ResourceType.COMPUTE,
                    provider=CloudProviderType.AWS,
                    region="us-east-1",
                    name="test-instance",
                ),
            ],
        )
        plan = await engine.generate_plan(intent)
        assert plan.step_count == EXPECTED_RESOURCE_COUNT
        assert plan.steps[0].name == "deploy-test-vpc"
        assert plan.steps[1].name == "deploy-test-instance"

    @pytest.mark.asyncio
    async def test_generate_default_steps(
        self, engine: RuleBasedPlanningEngine
    ) -> None:
        intent = DeploymentIntent(
            description="No resources",
            target_providers=[CloudProviderType.AWS],
            target_regions=["us-east-1"],
        )
        plan = await engine.generate_plan(intent)
        assert plan.step_count >= EXPECTED_RESOURCE_COUNT

    @pytest.mark.asyncio
    async def test_multi_provider_plan(
        self, engine: RuleBasedPlanningEngine
    ) -> None:
        intent = DeploymentIntent(
            description="Multi-cloud",
            target_providers=[CloudProviderType.AWS, CloudProviderType.GCP],
            target_regions=["us-east-1"],
        )
        plan = await engine.generate_plan(intent)
        providers = {step.provider for step in plan.steps}
        assert CloudProviderType.AWS in providers
        assert CloudProviderType.GCP in providers

    @pytest.mark.asyncio
    async def test_production_high_risk(
        self, engine: RuleBasedPlanningEngine
    ) -> None:
        intent = DeploymentIntent(
            description="Production deploy",
            target_providers=[CloudProviderType.AWS],
            environment="production",
        )
        plan = await engine.generate_plan(intent)
        assert plan.risk_assessment == "high"

    @pytest.mark.asyncio
    async def test_validate_valid_plan(
        self, engine: RuleBasedPlanningEngine
    ) -> None:
        intent = DeploymentIntent(
            description="Test",
            target_providers=[CloudProviderType.AWS],
            target_regions=["us-east-1"],
        )
        plan = await engine.generate_plan(intent)
        valid, errors = await engine.validate_plan(plan)
        assert valid
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_estimate_cost(
        self, engine: RuleBasedPlanningEngine
    ) -> None:
        intent = DeploymentIntent(
            description="Cost test",
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
        plan = await engine.generate_plan(intent)
        costs = await engine.estimate_cost(plan)
        assert "total_monthly" in costs
        assert costs["total_monthly"] > 0

    @pytest.mark.asyncio
    async def test_resource_ordering(
        self, engine: RuleBasedPlanningEngine
    ) -> None:
        """Network should come before compute in execution order."""
        intent = DeploymentIntent(
            description="Ordering test",
            target_providers=[CloudProviderType.AWS],
            resources=[
                ResourceSpec(
                    resource_type=ResourceType.COMPUTE,
                    provider=CloudProviderType.AWS,
                    region="us-east-1",
                    name="compute-1",
                ),
                ResourceSpec(
                    resource_type=ResourceType.NETWORK,
                    provider=CloudProviderType.AWS,
                    region="us-east-1",
                    name="network-1",
                ),
            ],
        )
        plan = await engine.generate_plan(intent)
        assert plan.steps[0].resource_spec.resource_type == ResourceType.NETWORK
        assert plan.steps[1].resource_spec.resource_type == ResourceType.COMPUTE
