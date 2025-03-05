"""Unit tests for cloud provider models."""

from __future__ import annotations

from orchestrator.domain.models.cloud_provider import (
    CloudCredential,
    CloudProviderType,
    CloudRegion,
    ProviderCapability,
    ResourceSpec,
    ResourceType,
)


class TestResourceSpec:
    def test_resource_identifier(self) -> None:
        spec = ResourceSpec(
            resource_type=ResourceType.COMPUTE,
            provider=CloudProviderType.AWS,
            region="us-east-1",
            name="test-instance",
        )
        assert spec.resource_identifier == "aws/us-east-1/compute/test-instance"

    def test_with_properties(self) -> None:
        spec = ResourceSpec(
            resource_type=ResourceType.DATABASE,
            provider=CloudProviderType.GCP,
            region="us-central1",
            name="my-db",
            properties={"engine": "postgres", "version": "16"},
            tags={"env": "prod"},
            dependencies=["vpc-1"],
        )
        assert spec.properties["engine"] == "postgres"
        assert len(spec.dependencies) == 1


class TestCloudProviderType:
    def test_values(self) -> None:
        assert CloudProviderType.AWS == "aws"
        assert CloudProviderType.AZURE == "azure"
        assert CloudProviderType.GCP == "gcp"


class TestResourceType:
    def test_all_types_exist(self) -> None:
        types = [
            ResourceType.COMPUTE, ResourceType.STORAGE, ResourceType.DATABASE,
            ResourceType.NETWORK, ResourceType.CONTAINER, ResourceType.SERVERLESS,
            ResourceType.LOAD_BALANCER, ResourceType.DNS, ResourceType.CDN,
            ResourceType.QUEUE, ResourceType.CACHE,
        ]
        assert len(types) == 11


class TestCloudRegion:
    def test_creation(self) -> None:
        region = CloudRegion(
            provider=CloudProviderType.AWS,
            region_id="us-east-1",
            display_name="US East (N. Virginia)",
        )
        assert region.available is True


class TestCloudCredential:
    def test_creation(self) -> None:
        cred = CloudCredential(
            provider=CloudProviderType.AWS,
            credential_ref="arn:aws:secretsmanager:us-east-1:123:secret:creds",
            role_arn="arn:aws:iam::123:role/deploy",
        )
        assert cred.project_id is None
        assert cred.subscription_id is None


class TestProviderCapability:
    def test_creation(self) -> None:
        cap = ProviderCapability(
            provider=CloudProviderType.AZURE,
            resource_type=ResourceType.COMPUTE,
            terraform_provider="azurerm",
            terraform_resource_type="azurerm_virtual_machine",
            supported_regions=["eastus", "westus2"],
        )
        assert len(cap.supported_regions) == 2
