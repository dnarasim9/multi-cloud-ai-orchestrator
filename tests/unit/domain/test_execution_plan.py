"""Unit tests for execution plan model."""

from __future__ import annotations

from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceSpec, ResourceType
from orchestrator.domain.models.deployment import ExecutionPlan, ExecutionStep


class TestExecutionPlan:
    def _make_step(self, name: str, deps: list[str] | None = None) -> ExecutionStep:
        return ExecutionStep(
            name=name,
            description=f"Step {name}",
            provider=CloudProviderType.AWS,
            resource_spec=ResourceSpec(
                resource_type=ResourceType.COMPUTE,
                provider=CloudProviderType.AWS,
                region="us-east-1",
                name=name,
            ),
            terraform_action="create",
            dependencies=deps or [],
        )

    def test_step_count(self) -> None:
        plan = ExecutionPlan(
            steps=[self._make_step("a"), self._make_step("b")],
        )
        assert plan.step_count == 2

    def test_get_step(self) -> None:
        step = self._make_step("find-me")
        plan = ExecutionPlan(steps=[step])
        found = plan.get_step(step.step_id)
        assert found is not None
        assert found.name == "find-me"

    def test_get_step_not_found(self) -> None:
        plan = ExecutionPlan(steps=[self._make_step("a")])
        assert plan.get_step("nonexistent") is None

    def test_execution_order_no_deps(self) -> None:
        steps = [self._make_step("a"), self._make_step("b"), self._make_step("c")]
        plan = ExecutionPlan(steps=steps)
        waves = plan.get_execution_order()
        assert len(waves) == 1
        assert len(waves[0]) == 3

    def test_execution_order_with_deps(self) -> None:
        step_a = self._make_step("network")
        step_b = self._make_step("compute", deps=[step_a.step_id])
        step_c = self._make_step("lb", deps=[step_b.step_id])
        plan = ExecutionPlan(steps=[step_a, step_b, step_c])
        waves = plan.get_execution_order()
        assert len(waves) == 3
        assert waves[0][0].name == "network"
        assert waves[1][0].name == "compute"
        assert waves[2][0].name == "lb"

    def test_parallel_waves(self) -> None:
        step_a = self._make_step("network")
        step_b = self._make_step("storage")
        step_c = self._make_step("compute", deps=[step_a.step_id])
        step_d = self._make_step("db", deps=[step_b.step_id])
        plan = ExecutionPlan(steps=[step_a, step_b, step_c, step_d])
        waves = plan.get_execution_order()
        assert len(waves) == 2
        assert len(waves[0]) == 2  # network + storage parallel
        assert len(waves[1]) == 2  # compute + db parallel
