"""Drift detection API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from orchestrator.api.dependencies.auth import require_permission
from orchestrator.api.dependencies.services import get_service_container, ServiceContainer
from orchestrator.api.schemas.drift_schemas import (
    DriftItemResponse,
    DriftReportResponse,
    ScanDriftRequest,
)
from orchestrator.domain.models.drift import DriftReport
from orchestrator.domain.models.user import Permission, User
from orchestrator.domain.services.drift_service import DriftDomainService, DriftScanError
from orchestrator.infrastructure.persistence.repositories.in_memory import (
    InMemoryDeploymentRepository,
    InMemoryDriftReportRepository,
)


router = APIRouter(prefix="/drift", tags=["drift"])


def _to_response(report: DriftReport) -> DriftReportResponse:
    """Map a drift report domain model to an API response."""
    return DriftReportResponse(
        id=report.id,
        deployment_id=report.deployment_id,
        scan_type=report.scan_type,
        items=[DriftItemResponse(**item.model_dump()) for item in report.items],
        summary=report.summary,
        has_drift=report.has_drift,
        critical_count=report.critical_count,
        high_count=report.high_count,
        max_severity=report.max_severity,
        created_at=report.created_at,
    )


def _build_drift_service(container: ServiceContainer) -> DriftDomainService:
    """Build a DriftDomainService wired to in-memory repos for demo use."""
    return DriftDomainService(
        deployment_repo=InMemoryDeploymentRepository(),
        drift_repo=InMemoryDriftReportRepository(),
        drift_detector=container.drift_detector,
        event_publisher=container.event_publisher,
    )


@router.post("/scan", response_model=DriftReportResponse)
async def scan_drift(
    request: ScanDriftRequest,
    _user: Annotated[User, Depends(require_permission(Permission.DRIFT_SCAN))],
    container: Annotated[ServiceContainer, Depends(get_service_container)],
) -> DriftReportResponse:
    """Trigger a drift detection scan for a deployment."""
    service = _build_drift_service(container)
    try:
        report = await service.scan_deployment(request.deployment_id)
    except DriftScanError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _to_response(report)
