"""Rule-based deployment planning engine."""

from __future__ import annotations

from typing import ClassVar

import structlog

from orchestrator.domain.models.cloud_provider import ResourceSpec, ResourceType
from orchestrator.domain.models.deployment import (
    DeploymentIntent,
    ExecutionPlan,
    ExecutionStep,
)
from orchestrator.domain.ports.services import PlanningEngine


logger = structlog.get_logger(__name__)


class RuleBasedPlanningEngine(PlanningEngine):
    """Rule-based planning engine that generates execution plans.

    Uses a strategy pattern to select the appropriate planning
    approach based on deployment intent characteristics. In production,
    this would integrate with an LLM for intelligent plan generation.
    """

    # Resource creation order for dependency resolution
    RESOURCE_PRIORITY: ClassVar[dict[ResourceType, int]] = {
        ResourceType.NETWORK: 1,
        ResourceType.DNS: 2,
        ResourceType.STORAGE: 3,
        ResourceType.DATABASE: 4,
        ResourceType.CACHE: 5,
        ResourceType.QUEUE: 6,
        ResourceType.COMPUTE: 7,
        ResourceType.CONTAINER: 8,
        ResourceType.SERVERLESS: 9,
        ResourceType.LOAD_BALANCER: 10,
        ResourceType.CDN: 11,
    }

    async def generate_plan(self, intent: DeploymentIntent) -> ExecutionPlan:
        """Generate an execution plan from deployment intent."""
        logger.info(
            "generating_plan",
            providers=[p.value for p in intent.target_providers],
            resource_count=len(intent.resources),
            strategy=intent.strategy.value,
        )

        steps = self._create_steps_from_resources(intent)

        if not steps:
            steps = self._create_default_steps(intent)

        self._resolve_dependencies(steps)

        estimated_duration = sum(s.estimated_duration_seconds for s in steps)
        risk = self._assess_risk(intent, steps)

        plan = ExecutionPlan(
            steps=steps,
            estimated_total_duration_seconds=estimated_duration,
            risk_assessment=risk,
            reasoning=self._generate_reasoning(intent, steps),
        )

        logger.info(
            "plan_generated",
            step_count=plan.step_count,
            estimated_duration=estimated_duration,
            risk=risk,
        )
        return plan

    async def validate_plan(self, plan: ExecutionPlan) -> tuple[bool, list[str]]:
        """Validate an execution plan."""
        errors: list[str] = []

        if not plan.steps:
            errors.append("Plan has no execution steps")

        step_ids = {step.step_id for step in plan.steps}
        for step in plan.steps:
            errors.extend(
                f"Step {step.name} depends on non-existent step {dep}"
                for dep in step.dependencies
                if dep not in step_ids
            )

        return len(errors) == 0, errors

    async def estimate_cost(self, plan: ExecutionPlan) -> dict[str, float]:
        """Estimate cost (simplified simulation)."""
        cost_per_resource: dict[ResourceType, float] = {
            ResourceType.COMPUTE: 50.0,
            ResourceType.STORAGE: 10.0,
            ResourceType.DATABASE: 75.0,
            ResourceType.NETWORK: 5.0,
            ResourceType.CONTAINER: 100.0,
            ResourceType.SERVERLESS: 20.0,
            ResourceType.LOAD_BALANCER: 25.0,
            ResourceType.CACHE: 40.0,
            ResourceType.QUEUE: 15.0,
            ResourceType.CDN: 30.0,
            ResourceType.DNS: 2.0,
        }

        costs: dict[str, float] = {}
        total = 0.0
        for step in plan.steps:
            resource_type = step.resource_spec.resource_type
            monthly_cost = cost_per_resource.get(resource_type, 25.0)
            costs[step.name] = monthly_cost
            total += monthly_cost

        costs["total_monthly"] = total
        return costs

    def _create_steps_from_resources(
        self, intent: DeploymentIntent
    ) -> list[ExecutionStep]:
        """Create execution steps from explicit resource specs."""
        sorted_resources = sorted(
            intent.resources,
            key=lambda r: self.RESOURCE_PRIORITY.get(r.resource_type, 99),
        )

        return [
            ExecutionStep(
                name=f"deploy-{resource.name}",
                description=(
                    f"Deploy {resource.resource_type.value} resource"
                    f" '{resource.name}' on {resource.provider.value}"
                ),
                provider=resource.provider,
                resource_spec=resource,
                terraform_action="create",
                estimated_duration_seconds=self._estimate_step_duration(resource),
            )
            for resource in sorted_resources
        ]

    def _create_default_steps(self, intent: DeploymentIntent) -> list[ExecutionStep]:
        """Create default infrastructure steps when no resources specified."""
        steps: list[ExecutionStep] = []
        for provider in intent.target_providers:
            region = intent.target_regions[0] if intent.target_regions else "us-east-1"

            # Network
            network_spec = ResourceSpec(
                resource_type=ResourceType.NETWORK,
                provider=provider,
                region=region,
                name=f"{intent.environment}-vpc",
                properties={"cidr_block": "10.0.0.0/16"},
                tags={"environment": intent.environment},
            )
            network_step = ExecutionStep(
                name=f"create-network-{provider.value}",
                description=f"Create VPC/VNet on {provider.value}",
                provider=provider,
                resource_spec=network_spec,
                terraform_action="create",
                estimated_duration_seconds=30,
            )
            steps.append(network_step)

            # Compute
            compute_spec = ResourceSpec(
                resource_type=ResourceType.COMPUTE,
                provider=provider,
                region=region,
                name=f"{intent.environment}-app",
                properties={"instance_type": "t3.medium"},
                tags={"environment": intent.environment},
                dependencies=[network_spec.resource_identifier],
            )
            compute_step = ExecutionStep(
                name=f"create-compute-{provider.value}",
                description=f"Create compute instance on {provider.value}",
                provider=provider,
                resource_spec=compute_spec,
                terraform_action="create",
                estimated_duration_seconds=60,
                dependencies=[network_step.step_id],
            )
            steps.append(compute_step)

        return steps

    def _resolve_dependencies(self, steps: list[ExecutionStep]) -> None:
        """Resolve resource-level dependencies to step-level dependencies.

        Maps each resource identifier to its owning step, then updates
        step-level dependency lists so the execution engine respects
        resource ordering.  Steps are replaced in-place within the list.
        """
        resource_to_step: dict[str, str] = {}
        for step in steps:
            resource_to_step[step.resource_spec.resource_identifier] = step.step_id

        for idx, step in enumerate(steps):
            new_deps = list(step.dependencies)
            changed = False
            for dep_resource in step.resource_spec.dependencies:
                dep_step_id = resource_to_step.get(dep_resource)
                if dep_step_id and dep_step_id not in new_deps:
                    new_deps.append(dep_step_id)
                    changed = True
            if changed:
                step_data = step.model_dump()
                step_data["dependencies"] = new_deps
                steps[idx] = ExecutionStep.model_validate(step_data)

    def _estimate_step_duration(self, resource: ResourceSpec) -> int:
        """Estimate execution duration for a resource."""
        durations: dict[ResourceType, int] = {
            ResourceType.NETWORK: 30,
            ResourceType.COMPUTE: 60,
            ResourceType.DATABASE: 120,
            ResourceType.CONTAINER: 90,
            ResourceType.STORAGE: 15,
            ResourceType.SERVERLESS: 30,
            ResourceType.LOAD_BALANCER: 45,
            ResourceType.CACHE: 60,
        }
        return durations.get(resource.resource_type, 60)

    def _assess_risk(
        self, intent: DeploymentIntent, steps: list[ExecutionStep]
    ) -> str:
        """Assess deployment risk level."""
        if intent.environment == "production":
            return "high"
        if len(intent.target_providers) > 1:
            return "medium"
        _max_simple_steps = 10
        if len(steps) > _max_simple_steps:
            return "medium"
        return "low"

    def _generate_reasoning(
        self, intent: DeploymentIntent, steps: list[ExecutionStep]
    ) -> str:
        """Generate human-readable reasoning for the plan."""
        providers = ", ".join(p.value for p in intent.target_providers)
        return (
            f"Generated {len(steps)} execution steps for deployment to {providers} "
            f"using {intent.strategy.value} strategy in {intent.environment} environment. "
            f"Risk assessment: {self._assess_risk(intent, steps)}."
        )
