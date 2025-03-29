"""Unit tests for Terraform executor."""

from __future__ import annotations

import os
import tempfile

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceSpec, ResourceType
from orchestrator.infrastructure.terraform.executor import SimulatedTerraformExecutor


@pytest.fixture
def executor() -> SimulatedTerraformExecutor:
    return SimulatedTerraformExecutor()


@pytest.fixture
def work_dir(tmp_path: object) -> str:
    """Provide a temporary working directory for Terraform tests."""
    return str(tmp_path)


class TestTerraformExecutor:
    @pytest.mark.asyncio
    async def test_init(self, executor: SimulatedTerraformExecutor, work_dir: str) -> None:
        success, output = await executor.init(work_dir, CloudProviderType.AWS)
        assert success
        assert "initialized" in output.lower()

    @pytest.mark.asyncio
    async def test_plan(self, executor: SimulatedTerraformExecutor, work_dir: str) -> None:
        success, output = await executor.plan(work_dir)
        assert success
        assert "Plan" in output

    @pytest.mark.asyncio
    async def test_apply(self, executor: SimulatedTerraformExecutor, work_dir: str) -> None:
        success, output = await executor.apply(work_dir)
        assert success
        assert "Apply complete" in output

    @pytest.mark.asyncio
    async def test_destroy(self, executor: SimulatedTerraformExecutor, work_dir: str) -> None:
        success, output = await executor.destroy(work_dir)
        assert success
        assert "Destroy complete" in output

    @pytest.mark.asyncio
    async def test_generate_config(self, executor: SimulatedTerraformExecutor) -> None:
        spec = ResourceSpec(
            resource_type=ResourceType.COMPUTE,
            provider=CloudProviderType.AWS,
            region="us-east-1",
            name="test-instance",
            properties={"instance_type": "t3.medium", "ami": "ami-12345"},
            tags={"environment": "test"},
        )
        gen_dir = tempfile.mkdtemp()
        hcl = await executor.generate_config(spec, gen_dir)
        assert "aws_instance" in hcl
        assert "test-instance" in hcl
        assert "t3.medium" in hcl
        assert os.path.exists(os.path.join(gen_dir, "main.tf"))

    @pytest.mark.asyncio
    async def test_show_state(self, executor: SimulatedTerraformExecutor, work_dir: str) -> None:
        await executor.apply(work_dir)
        state = await executor.show_state(work_dir)
        assert isinstance(state, dict)
