"""Deployment API routes."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from orchestrator.api.dependencies.auth import require_permission
from orchestrator.api.dependencies.services import get_service_container, ServiceContainer
from orchestrator.api.schemas.deployment_schemas import (
    ApproveDeploymentRequest,
    CreateDeploymentRequest,
    DeploymentResponse,
    ExecutionPlanResponse,
    StepResultResponse,
)
from orchestrator.domain.models.cloud_provider import ResourceSpec
from orchestrator.domain.models.deployment import Deployment, DeploymentIntent
from orchestrator.domain.models.user import Permission, User
from orchestrator.domain.services.deployment_service import (
    DeploymentDomainService,
    DeploymentLockError,
    DeploymentNotFoundError,
    DeploymentPlanMissingError,
)
from orchestrator.infrastructure.persistence.repositories.in_memory import (
    InMemoryDeploymentRepository,
    InMemoryTaskRepository,
)


router = APIRouter(prefix="/deployments", tags=["deployments"])

# Thread-safe lazy singleton for the demo deployment service.
_init_lock = asyncio.Lock()
_state: dict[str, DeploymentDomainService | None] = {"service": None}


def _to_response(deployment: Deployment) -> DeploymentResponse:
    """Map domain model to API response."""
    plan_response = None
    if deployment.plan:
        plan_response = ExecutionPlanResponse(
            plan_id=deployment.plan.plan_id,
            step_count=deployment.plan.step_count,
            estimated_total_duration_seconds=deployment.plan.estimated_total_duration_seconds,
            risk_assessment=deployment.plan.risk_assessment,
            reasoning=deployment.plan.reasoning,
            steps=[s.model_dump() for s in deployment.plan.steps],
        )

    return DeploymentResponse(
        id=deployment.id,
        name=deployment.name,
        status=deployment.status,
        environment=deployment.intent.environment,
        strategy=deployment.intent.strategy,
        providers=deployment.intent.target_providers,
        plan=plan_response,
        step_results=[
            StepResultResponse(**r.model_dump()) for r in deployment.step_results
        ],
        progress_percentage=deployment.progress_percentage,
        error_message=deployment.error_message,
        initiated_by=deployment.initiated_by,
        tenant_id=deployment.tenant_id,
        created_at=deployment.created_at,
        updated_at=deployment.updated_at,
    )


def _build_deployment_service(container: ServiceContainer) -> DeploymentDomainService:
    """Build DeploymentDomainService from in-memory repos for demo."""
    return DeploymentDomainService(
        deployment_repo=InMemoryDeploymentRepository(),
        task_repo=InMemoryTaskRepository(),
        planning_engine=container.planning_engine,
        event_publisher=container.event_publisher,
        lock_service=container.lock_service,
    )


async def _get_deployment_service(
    container: Annotated[ServiceContainer, Depends(get_service_container)],
) -> DeploymentDomainService:
    """Return the singleton deployment service, creating it once in a thread-safe way."""
    if _state["service"] is None:
        async with _init_lock:
            # Double-check after acquiring lock
            if _state["service"] is None:
                _state["service"] = _build_deployment_service(container)
    service = _state["service"]
    assert service is not None  # guaranteed by double-check above
    return service


@router.post(
    "",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_deployment(
    request: CreateDeploymentRequest,
    user: Annotated[User, Depends(require_permission(Permission.DEPLOYMENT_CREATE))],
    service: Annotated[DeploymentDomainService, Depends(_get_deployment_service)],
) -> DeploymentResponse:
    """Create a new deployment from intent."""
    intent = DeploymentIntent(
        description=request.description,
        target_providers=request.target_providers,
        target_regions=request.target_regions,
        resources=[ResourceSpec(**r.model_dump()) for r in request.resources],
        strategy=request.strategy,
        auto_approve=request.auto_approve,
        rollback_on_failure=request.rollback_on_failure,
        environment=request.environment,
        parameters=request.parameters,
    )
    deployment = await service.create_deployment(
        intent=intent,
        initiated_by=user.id,
        tenant_id=user.tenant_id,
    )
    return _to_response(deployment)


@router.post("/{deployment_id}/plan", response_model=DeploymentResponse)
async def plan_deployment(
    deployment_id: str,
    _user: Annotated[User, Depends(require_permission(Permission.DEPLOYMENT_CREATE))],
    service: Annotated[DeploymentDomainService, Depends(_get_deployment_service)],
) -> DeploymentResponse:
    """Generate an execution plan for a deployment."""
    try:
        deployment = await service.plan_deployment(deployment_id)
    except DeploymentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except DeploymentLockError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _to_response(deployment)


@router.post("/{deployment_id}/approve", response_model=DeploymentResponse)
async def approve_deployment(
    deployment_id: str,
    request: ApproveDeploymentRequest,
    _user: Annotated[User, Depends(require_permission(Permission.DEPLOYMENT_APPROVE))],
    service: Annotated[DeploymentDomainService, Depends(_get_deployment_service)],
) -> DeploymentResponse:
    """Approve a deployment for execution."""
    try:
        deployment = await service.approve_deployment(deployment_id, request.approved_by)
    except DeploymentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _to_response(deployment)


@router.post("/{deployment_id}/execute", response_model=dict)
async def execute_deployment(
    deployment_id: str,
    _user: Annotated[User, Depends(require_permission(Permission.DEPLOYMENT_CREATE))],
    service: Annotated[DeploymentDomainService, Depends(_get_deployment_service)],
) -> dict[str, str | int]:
    """Start execution of a deployment plan."""
    try:
        tasks = await service.execute_deployment(deployment_id)
    except DeploymentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except DeploymentPlanMissingError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"deployment_id": deployment_id, "tasks_created": len(tasks)}


@router.post("/{deployment_id}/rollback", response_model=DeploymentResponse)
async def rollback_deployment(
    deployment_id: str,
    _user: Annotated[User, Depends(require_permission(Permission.DEPLOYMENT_ROLLBACK))],
    service: Annotated[DeploymentDomainService, Depends(_get_deployment_service)],
) -> DeploymentResponse:
    """Rollback a deployment."""
    try:
        deployment = await service.rollback_deployment(deployment_id)
    except DeploymentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _to_response(deployment)
