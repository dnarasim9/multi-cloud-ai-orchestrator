"""Unit tests for deployment domain model."""

from __future__ import annotations

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceSpec, ResourceType
from orchestrator.domain.models.deployment import (
    Deployment,
    DeploymentIntent,
    DeploymentStatus,
    ExecutionPlan,
    ExecutionStep,
    InvalidStateTransitionError,
    StepResult,
    VALID_TRANSITIONS,
)


class TestDeploymentStateMachine:
    """Tests for deployment state machine transitions."""

    def test_initial_status_is_pending(self, sample_deployment: Deployment) -> None:
        assert sample_deployment.status == DeploymentStatus.PENDING

    def test_start_planning_from_pending(self, sample_deployment: Deployment) -> None:
        sample_deployment.start_planning()
        assert sample_deployment.status == DeploymentStatus.PLANNING

    def test_cannot_start_execution_from_pending(self, sample_deployment: Deployment) -> None:
        with pytest.raises(InvalidStateTransitionError):
            sample_deployment.start_execution()

    def test_set_plan_moves_to_awaiting_approval(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(sample_execution_plan)
        assert sample_deployment.status == DeploymentStatus.AWAITING_APPROVAL
        assert sample_deployment.plan is not None

    def test_auto_approve_skips_awaiting(self, sample_resource_spec: ResourceSpec) -> None:
        intent = DeploymentIntent(
            description="Auto-approve test",
            target_providers=[CloudProviderType.AWS],
            resources=[sample_resource_spec],
            auto_approve=True,
        )
        deployment = Deployment(
            name="auto-approve",
            intent=intent,
            initiated_by="test",
            tenant_id="test",
        )
        deployment.start_planning()

        step = ExecutionStep(
            name="test-step",
            description="test",
            provider=CloudProviderType.AWS,
            resource_spec=sample_resource_spec,
            terraform_action="create",
        )
        plan = ExecutionPlan(steps=[step])
        deployment.set_plan(plan)
        assert deployment.status == DeploymentStatus.APPROVED

    def test_approve_from_awaiting(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(sample_execution_plan)
        sample_deployment.approve(approved_by="admin")
        assert sample_deployment.status == DeploymentStatus.APPROVED

    def test_execute_from_approved(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(sample_execution_plan)
        sample_deployment.approve(approved_by="admin")
        sample_deployment.start_execution()
        assert sample_deployment.status == DeploymentStatus.EXECUTING

    def test_complete_flow(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(sample_execution_plan)
        sample_deployment.approve(approved_by="admin")
        sample_deployment.start_execution()
        sample_deployment.start_verification()
        sample_deployment.complete()
        assert sample_deployment.status == DeploymentStatus.COMPLETED
        assert sample_deployment.is_terminal

    def test_fail_from_executing(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(sample_execution_plan)
        sample_deployment.approve(approved_by="admin")
        sample_deployment.start_execution()
        sample_deployment.fail("Test failure")
        assert sample_deployment.status == DeploymentStatus.FAILED
        assert sample_deployment.error_message == "Test failure"

    def test_rollback_from_failed(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(sample_execution_plan)
        sample_deployment.approve(approved_by="admin")
        sample_deployment.start_execution()
        sample_deployment.fail("Error")
        sample_deployment.start_rollback()
        assert sample_deployment.status == DeploymentStatus.ROLLING_BACK

    def test_rollback_complete(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(sample_execution_plan)
        sample_deployment.approve(approved_by="admin")
        sample_deployment.start_execution()
        sample_deployment.fail("Error")
        sample_deployment.start_rollback()
        sample_deployment.complete_rollback()
        assert sample_deployment.status == DeploymentStatus.ROLLED_BACK
        assert sample_deployment.is_terminal

    def test_cancel_from_pending(self, sample_deployment: Deployment) -> None:
        sample_deployment.cancel()
        assert sample_deployment.status == DeploymentStatus.CANCELLED
        assert sample_deployment.is_terminal

    def test_cannot_transition_from_completed(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(sample_execution_plan)
        sample_deployment.approve(approved_by="admin")
        sample_deployment.start_execution()
        sample_deployment.start_verification()
        sample_deployment.complete()
        with pytest.raises(InvalidStateTransitionError):
            sample_deployment.fail("Should not work")

    def test_all_valid_transitions_exist(self) -> None:
        """Verify that all statuses have entries in the transition map."""
        for status in DeploymentStatus:
            assert status in VALID_TRANSITIONS


class TestDeploymentProperties:
    """Tests for deployment computed properties."""

    def test_progress_no_plan(self, sample_deployment: Deployment) -> None:
        assert sample_deployment.progress_percentage == 0.0

    def test_progress_with_results(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.plan = sample_execution_plan
        result = StepResult(
            step_id=sample_execution_plan.steps[0].step_id,
            success=True,
            output="done",
        )
        sample_deployment.step_results.append(result)
        assert sample_deployment.progress_percentage == 100.0

    def test_version_increments_on_touch(self, sample_deployment: Deployment) -> None:
        initial_version = sample_deployment.version
        sample_deployment.touch()
        assert sample_deployment.version == initial_version + 1


class TestDomainEvents:
    """Tests for deployment domain events."""

    def test_plan_generated_event(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(sample_execution_plan)
        events = sample_deployment.collect_events()
        event_types = [e.event_type for e in events]
        assert "deployment.plan_generated" in event_types

    def test_completed_event(
        self, sample_deployment: Deployment, sample_execution_plan: ExecutionPlan
    ) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(sample_execution_plan)
        sample_deployment.approve(approved_by="admin")
        sample_deployment.start_execution()
        sample_deployment.start_verification()
        sample_deployment.collect_events()  # clear
        sample_deployment.complete()
        events = sample_deployment.collect_events()
        assert any(e.event_type == "deployment.completed" for e in events)

    def test_collect_clears_events(self, sample_deployment: Deployment) -> None:
        sample_deployment.start_planning()
        sample_deployment.set_plan(
            ExecutionPlan(steps=[
                ExecutionStep(
                    name="t",
                    description="t",
                    provider=CloudProviderType.AWS,
                    resource_spec=ResourceSpec(
                        resource_type=ResourceType.COMPUTE,
                        provider=CloudProviderType.AWS,
                        region="us-east-1",
                        name="t",
                    ),
                    terraform_action="create",
                )
            ])
        )
        events = sample_deployment.collect_events()
        assert len(events) > 0
        assert len(sample_deployment.collect_events()) == 0
