"""Cloud provider domain models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from orchestrator.domain.models.base import ValueObject


class CloudProviderType(str, Enum):
    """Supported cloud providers."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class ResourceType(str, Enum):
    """Types of cloud resources."""

    COMPUTE = "compute"
    STORAGE = "storage"
    DATABASE = "database"
    NETWORK = "network"
    CONTAINER = "container"
    SERVERLESS = "serverless"
    LOAD_BALANCER = "load_balancer"
    DNS = "dns"
    CDN = "cdn"
    QUEUE = "queue"
    CACHE = "cache"


class CloudRegion(ValueObject):
    """Cloud region value object."""

    provider: CloudProviderType
    region_id: str
    display_name: str
    available: bool = True


class CloudCredential(ValueObject):
    """Cloud credential reference (never stores actual secrets)."""

    provider: CloudProviderType
    credential_ref: str  # Reference to secrets manager
    role_arn: str | None = None
    project_id: str | None = None
    subscription_id: str | None = None


class ResourceSpec(ValueObject):
    """Specification for a cloud resource."""

    resource_type: ResourceType
    provider: CloudProviderType
    region: str
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, str] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)

    @property
    def resource_identifier(self) -> str:
        return f"{self.provider.value}/{self.region}/{self.resource_type.value}/{self.name}"


class ProviderCapability(ValueObject):
    """Describes a cloud provider's capability for a resource type."""

    provider: CloudProviderType
    resource_type: ResourceType
    terraform_provider: str
    terraform_resource_type: str
    supported_regions: list[str] = Field(default_factory=list)
    default_properties: dict[str, Any] = Field(default_factory=dict)
