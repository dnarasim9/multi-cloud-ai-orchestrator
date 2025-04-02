"""Unit tests for API schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from orchestrator.api.schemas.auth_schemas import LoginRequest, RegisterRequest
from orchestrator.api.schemas.deployment_schemas import (
    CreateDeploymentRequest,
    ResourceSpecRequest,
)
from orchestrator.api.schemas.drift_schemas import ScanDriftRequest
from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceType
from orchestrator.domain.models.deployment import DeploymentStrategy


class TestCreateDeploymentRequest:
    def test_valid_request(self) -> None:
        req = CreateDeploymentRequest(
            description="Deploy app",
            target_providers=[CloudProviderType.AWS],
            environment="staging",
        )
        assert req.description == "Deploy app"
        assert req.strategy == DeploymentStrategy.ROLLING

    def test_empty_description_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateDeploymentRequest(
                description="",
                target_providers=[CloudProviderType.AWS],
            )

    def test_no_providers_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateDeploymentRequest(
                description="Test",
                target_providers=[],
            )

    def test_invalid_environment_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CreateDeploymentRequest(
                description="Test",
                target_providers=[CloudProviderType.AWS],
                environment="invalid",
            )

    def test_with_resources(self) -> None:
        req = CreateDeploymentRequest(
            description="Test",
            target_providers=[CloudProviderType.AWS],
            resources=[
                ResourceSpecRequest(
                    resource_type=ResourceType.COMPUTE,
                    provider=CloudProviderType.AWS,
                    region="us-east-1",
                    name="instance-1",
                ),
            ],
        )
        assert len(req.resources) == 1


class TestLoginRequest:
    def test_valid(self) -> None:
        req = LoginRequest(username="user123", password="password123")
        assert req.username == "user123"

    def test_short_username(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(username="ab", password="password123")

    def test_short_password(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(username="user123", password="short")


class TestRegisterRequest:
    def test_valid(self) -> None:
        req = RegisterRequest(
            username="newuser",
            email="new@example.com",
            password="password123",
        )
        assert req.email == "new@example.com"

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="newuser",
                email="not-an-email",
                password="password123",
            )


class TestScanDriftRequest:
    def test_valid(self) -> None:
        req = ScanDriftRequest(deployment_id="d-1")
        assert req.auto_remediate is False
