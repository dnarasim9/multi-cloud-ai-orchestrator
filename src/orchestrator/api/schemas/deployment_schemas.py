"""API schemas for deployment endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from orchestrator.domain.models.cloud_provider import CloudProviderType, ResourceType
from orchestrator.domain.models.deployment import DeploymentStatus, DeploymentStrategy


class ResourceSpecRequest(BaseModel):
    resource_type: ResourceType
    provider: CloudProviderType
    region: str
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, str] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class CreateDeploymentRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=1000)
    target_providers: list[CloudProviderType] = Field(..., min_length=1)
    target_regions: list[str] = Field(default_factory=list)
    resources: list[ResourceSpecRequest] = Field(default_factory=list)
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    auto_approve: bool = False
    rollback_on_failure: bool = True
    environment: str = Field(default="staging", pattern="^(development|staging|production)$")
    parameters: dict[str, Any] = Field(default_factory=dict)


class ApproveDeploymentRequest(BaseModel):
    approved_by: str = Field(..., min_length=1)


class StepResultResponse(BaseModel):
    step_id: str
    success: bool
    output: str = ""
    error_message: str = ""
    duration_seconds: float = 0.0
    attempt_number: int = 1


class ExecutionPlanResponse(BaseModel):
    plan_id: str
    step_count: int
    estimated_total_duration_seconds: int
    risk_assessment: str
    reasoning: str
    steps: list[dict[str, Any]] = Field(default_factory=list)


class DeploymentResponse(BaseModel):
    id: str
    name: str
    status: DeploymentStatus
    environment: str
    strategy: DeploymentStrategy
    providers: list[CloudProviderType]
    plan: ExecutionPlanResponse | None = None
    step_results: list[StepResultResponse] = Field(default_factory=list)
    progress_percentage: float = 0.0
    error_message: str = ""
    initiated_by: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeploymentListResponse(BaseModel):
    items: list[DeploymentResponse]
    total: int
    limit: int
    offset: int
