"""Service port interfaces (hexagonal architecture)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from orchestrator.domain.models.cloud_provider import CloudProviderType
from orchestrator.domain.models.deployment import DeploymentIntent, ExecutionPlan
from orchestrator.domain.models.drift import DriftReport


class PlanningEngine(ABC):
    """Port for the deployment planning engine."""

    @abstractmethod
    async def generate_plan(self, intent: DeploymentIntent) -> ExecutionPlan:
        """Generate an execution plan from deployment intent."""

    @abstractmethod
    async def validate_plan(self, plan: ExecutionPlan) -> tuple[bool, list[str]]:
        """Validate an execution plan. Returns (is_valid, errors)."""

    @abstractmethod
    async def estimate_cost(self, plan: ExecutionPlan) -> dict[str, float]:
        """Estimate the cost of executing a plan."""


class TerraformExecutor(ABC):
    """Port for Terraform execution."""

    @abstractmethod
    async def init(self, working_dir: str, provider: CloudProviderType) -> tuple[bool, str]:
        """Initialize Terraform in a working directory."""

    @abstractmethod
    async def plan(self, working_dir: str) -> tuple[bool, str]:
        """Run terraform plan."""

    @abstractmethod
    async def apply(self, working_dir: str, auto_approve: bool = True) -> tuple[bool, str]:
        """Run terraform apply."""

    @abstractmethod
    async def destroy(self, working_dir: str, auto_approve: bool = True) -> tuple[bool, str]:
        """Run terraform destroy."""

    @abstractmethod
    async def show_state(self, working_dir: str) -> dict[str, Any]:
        """Get current terraform state."""

    @abstractmethod
    async def generate_config(
        self, resource_spec: Any, working_dir: str
    ) -> str:
        """Generate Terraform HCL configuration for a resource spec."""


class DriftDetector(ABC):
    """Port for drift detection."""

    @abstractmethod
    async def detect_drift(
        self, deployment_id: str, expected_state: dict[str, Any]
    ) -> DriftReport:
        """Detect configuration drift for a deployment."""

    @abstractmethod
    async def get_current_state(
        self, provider: CloudProviderType, resource_ids: list[str]
    ) -> dict[str, Any]:
        """Get current state of resources from cloud provider."""


class EventPublisher(ABC):
    """Port for publishing domain events."""

    @abstractmethod
    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish an event."""

    @abstractmethod
    async def publish_batch(self, events: list[tuple[str, dict[str, Any]]]) -> None:
        """Publish a batch of events."""


class DistributedLock(ABC):
    """Port for distributed locking."""

    @abstractmethod
    async def acquire(self, resource_id: str, ttl_seconds: int = 30) -> bool:
        """Acquire a distributed lock."""

    @abstractmethod
    async def release(self, resource_id: str) -> bool:
        """Release a distributed lock."""

    @abstractmethod
    async def extend(self, resource_id: str, ttl_seconds: int = 30) -> bool:
        """Extend the TTL of an existing lock."""

    @abstractmethod
    async def is_locked(self, resource_id: str) -> bool:
        """Check if a resource is locked."""


class CacheService(ABC):
    """Port for caching."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set a value in cache."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value from cache."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""


class HealthChecker(ABC):
    """Port for health checking deployed resources."""

    @abstractmethod
    async def check_resource(
        self, provider: CloudProviderType, resource_id: str
    ) -> tuple[bool, str]:
        """Check health of a deployed resource. Returns (healthy, message)."""

    @abstractmethod
    async def check_deployment(self, deployment_id: str) -> dict[str, Any]:
        """Check health of all resources in a deployment."""
