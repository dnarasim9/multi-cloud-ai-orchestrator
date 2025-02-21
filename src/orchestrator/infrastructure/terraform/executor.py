"""Terraform executor implementation."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from typing import Any

import structlog

from orchestrator.domain.models.cloud_provider import (
    CloudProviderType,
    ResourceSpec,
    ResourceType,
)
from orchestrator.domain.ports.services import TerraformExecutor


logger = structlog.get_logger(__name__)

# Terraform provider configurations (simulated)
PROVIDER_CONFIGS: dict[CloudProviderType, dict[str, str]] = {
    CloudProviderType.AWS: {
        "source": "hashicorp/aws",
        "version": "~> 5.0",
    },
    CloudProviderType.AZURE: {
        "source": "hashicorp/azurerm",
        "version": "~> 3.0",
    },
    CloudProviderType.GCP: {
        "source": "hashicorp/google",
        "version": "~> 5.0",
    },
}

# Resource type to Terraform resource mapping
RESOURCE_TERRAFORM_MAP: dict[tuple[CloudProviderType, ResourceType], str] = {
    (CloudProviderType.AWS, ResourceType.COMPUTE): "aws_instance",
    (CloudProviderType.AWS, ResourceType.STORAGE): "aws_s3_bucket",
    (CloudProviderType.AWS, ResourceType.DATABASE): "aws_db_instance",
    (CloudProviderType.AWS, ResourceType.NETWORK): "aws_vpc",
    (CloudProviderType.AWS, ResourceType.CONTAINER): "aws_ecs_cluster",
    (CloudProviderType.AWS, ResourceType.SERVERLESS): "aws_lambda_function",
    (CloudProviderType.AWS, ResourceType.LOAD_BALANCER): "aws_lb",
    (CloudProviderType.AWS, ResourceType.CACHE): "aws_elasticache_cluster",
    (CloudProviderType.AZURE, ResourceType.COMPUTE): "azurerm_virtual_machine",
    (CloudProviderType.AZURE, ResourceType.STORAGE): "azurerm_storage_account",
    (CloudProviderType.AZURE, ResourceType.DATABASE): "azurerm_postgresql_server",
    (CloudProviderType.AZURE, ResourceType.NETWORK): "azurerm_virtual_network",
    (CloudProviderType.AZURE, ResourceType.CONTAINER): "azurerm_kubernetes_cluster",
    (CloudProviderType.GCP, ResourceType.COMPUTE): "google_compute_instance",
    (CloudProviderType.GCP, ResourceType.STORAGE): "google_storage_bucket",
    (CloudProviderType.GCP, ResourceType.DATABASE): "google_sql_database_instance",
    (CloudProviderType.GCP, ResourceType.NETWORK): "google_compute_network",
    (CloudProviderType.GCP, ResourceType.CONTAINER): "google_container_cluster",
}


class SimulatedTerraformExecutor(TerraformExecutor):
    """Simulated Terraform executor for development/testing.

    Generates realistic Terraform HCL configurations and simulates
    plan/apply/destroy operations without requiring actual Terraform
    installation or cloud credentials.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = base_dir or tempfile.mkdtemp(prefix="tf-orchestrator-")
        self._state: dict[str, dict[str, Any]] = {}

    async def init(
        self, working_dir: str, provider: CloudProviderType
    ) -> tuple[bool, str]:
        """Simulate terraform init."""
        config = PROVIDER_CONFIGS.get(provider)
        if not config:
            return False, f"Unsupported provider: {provider.value}"

        os.makedirs(working_dir, exist_ok=True)

        logger.info(
            "terraform_init",
            working_dir=working_dir,
            provider=provider.value,
        )

        # Simulate initialization delay
        await asyncio.sleep(0.1)
        return True, f"Terraform initialized for {provider.value}"

    async def plan(self, working_dir: str) -> tuple[bool, str]:
        """Simulate terraform plan."""
        logger.info("terraform_plan", working_dir=working_dir)
        await asyncio.sleep(0.1)
        return True, "Plan: 1 to add, 0 to change, 0 to destroy."

    async def apply(
        self, working_dir: str, auto_approve: bool = True  # noqa: ARG002
    ) -> tuple[bool, str]:
        """Simulate terraform apply."""
        logger.info("terraform_apply", working_dir=working_dir)
        await asyncio.sleep(0.2)

        resource_id = f"sim-{os.path.basename(working_dir)}"
        self._state[resource_id] = {
            "status": "created",
            "working_dir": working_dir,
        }

        return True, "Apply complete! Resources: 1 added, 0 changed, 0 destroyed."

    async def destroy(
        self, working_dir: str, auto_approve: bool = True  # noqa: ARG002
    ) -> tuple[bool, str]:
        """Simulate terraform destroy."""
        logger.info("terraform_destroy", working_dir=working_dir)
        await asyncio.sleep(0.1)

        resource_id = f"sim-{os.path.basename(working_dir)}"
        self._state.pop(resource_id, None)

        return True, "Destroy complete! Resources: 1 destroyed."

    async def show_state(self, working_dir: str) -> dict[str, Any]:  # noqa: ARG002
        """Return simulated state."""
        return dict(self._state)

    async def generate_config(
        self, resource_spec: Any, working_dir: str
    ) -> str:
        """Generate Terraform HCL configuration."""
        if isinstance(resource_spec, dict):
            spec = ResourceSpec.model_validate(resource_spec)
        else:
            spec = resource_spec

        tf_resource = RESOURCE_TERRAFORM_MAP.get(
            (spec.provider, spec.resource_type),
            f"{spec.provider.value}_{spec.resource_type.value}",
        )

        provider_config = PROVIDER_CONFIGS.get(spec.provider, {})

        hcl = f'''terraform {{
  required_providers {{
    {spec.provider.value} = {{
      source  = "{provider_config.get('source', 'hashicorp/' + spec.provider.value)}"
      version = "{provider_config.get('version', '~> 1.0')}"
    }}
  }}
}}

resource "{tf_resource}" "{spec.name}" {{
  # Region: {spec.region}
'''
        for key, value in spec.properties.items():
            if isinstance(value, str):
                hcl += f'  {key} = "{value}"\n'
            else:
                hcl += f'  {key} = {json.dumps(value)}\n'

        if spec.tags:
            hcl += "\n  tags = {\n"
            for tag_key, tag_value in spec.tags.items():
                hcl += f'    {tag_key} = "{tag_value}"\n'
            hcl += "  }\n"

        hcl += "}\n"

        config_path = os.path.join(working_dir, "main.tf")
        os.makedirs(working_dir, exist_ok=True)
        with open(config_path, "w") as f:
            f.write(hcl)

        return hcl
