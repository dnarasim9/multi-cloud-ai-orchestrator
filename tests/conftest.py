"""Shared test fixtures."""

from __future__ import annotations

import pytest

from orchestrator.config import AuthSettings, Environment, Settings
from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceSpec, ResourceType
from orchestrator.domain.models.deployment import (
    Deployment,
    DeploymentIntent,
    DeploymentStrategy,
    ExecutionPlan,
    ExecutionStep,
)
from orchestrator.domain.models.user import Role, User
from orchestrator.infrastructure.ai.drift_detector import SimulatedDriftDetector
from orchestrator.infrastructure.ai.planning_engine import RuleBasedPlanningEngine
from orchestrator.infrastructure.auth.jwt_handler import JWTHandler
from orchestrator.infrastructure.messaging.event_publisher import InMemoryEventPublisher
from orchestrator.infrastructure.persistence.repositories.in_memory import (
    InMemoryDeploymentRepository,
    InMemoryDriftReportRepository,
    InMemoryTaskRepository,
    InMemoryUserRepository,
)
from orchestrator.infrastructure.terraform.executor import SimulatedTerraformExecutor


@pytest.fixture(autouse=True)
def clear_stores() -> None:
    """Clear in-memory stores before each test."""
    InMemoryDeploymentRepository.clear()
    InMemoryTaskRepository.clear()
    InMemoryDriftReportRepository.clear()
    InMemoryUserRepository.clear()


@pytest.fixture
def settings() -> Settings:
    return Settings(environment=Environment.TESTING, debug=True)


@pytest.fixture
def auth_settings() -> AuthSettings:
    return AuthSettings(
        secret_key="test-secret-key",
        algorithm="HS256",
        access_token_expire_minutes=30,
    )


@pytest.fixture
def jwt_handler(auth_settings: AuthSettings) -> JWTHandler:
    return JWTHandler(auth_settings)


@pytest.fixture
def deployment_repo() -> InMemoryDeploymentRepository:
    return InMemoryDeploymentRepository()


@pytest.fixture
def task_repo() -> InMemoryTaskRepository:
    return InMemoryTaskRepository()


@pytest.fixture
def drift_repo() -> InMemoryDriftReportRepository:
    return InMemoryDriftReportRepository()


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def event_publisher() -> InMemoryEventPublisher:
    return InMemoryEventPublisher()


@pytest.fixture
def planning_engine() -> RuleBasedPlanningEngine:
    return RuleBasedPlanningEngine()


@pytest.fixture
def terraform_executor() -> SimulatedTerraformExecutor:
    return SimulatedTerraformExecutor()


@pytest.fixture
def drift_detector() -> SimulatedDriftDetector:
    return SimulatedDriftDetector(drift_probability=0.0)


@pytest.fixture
def sample_resource_spec() -> ResourceSpec:
    return ResourceSpec(
        resource_type=ResourceType.COMPUTE,
        provider=CloudProviderType.AWS,
        region="us-east-1",
        name="test-instance",
        properties={"instance_type": "t3.medium"},
        tags={"environment": "test"},
    )


@pytest.fixture
def sample_intent(sample_resource_spec: ResourceSpec) -> DeploymentIntent:
    return DeploymentIntent(
        description="Test deployment",
        target_providers=[CloudProviderType.AWS],
        target_regions=["us-east-1"],
        resources=[sample_resource_spec],
        strategy=DeploymentStrategy.ROLLING,
        auto_approve=False,
        rollback_on_failure=True,
        environment="staging",
    )


@pytest.fixture
def sample_deployment(sample_intent: DeploymentIntent) -> Deployment:
    return Deployment(
        name="test-deployment",
        intent=sample_intent,
        initiated_by="test-user",
        tenant_id="test-tenant",
    )


@pytest.fixture
def sample_execution_plan(sample_resource_spec: ResourceSpec) -> ExecutionPlan:
    step = ExecutionStep(
        name="deploy-test-instance",
        description="Deploy test compute instance",
        provider=CloudProviderType.AWS,
        resource_spec=sample_resource_spec,
        terraform_action="create",
        estimated_duration_seconds=60,
    )
    return ExecutionPlan(
        steps=[step],
        estimated_total_duration_seconds=60,
        risk_assessment="low",
        reasoning="Test plan for a single compute instance",
    )


@pytest.fixture
def sample_user() -> User:
    return User(
        username="testuser",
        email="test@example.com",
        hashed_password=JWTHandler.hash_password("testpassword123"),
        role=Role.OPERATOR,
        tenant_id="test-tenant",
    )


@pytest.fixture
def admin_user() -> User:
    return User(
        username="admin",
        email="admin@example.com",
        hashed_password=JWTHandler.hash_password("adminpassword123"),
        role=Role.ADMIN,
        tenant_id="test-tenant",
    )
