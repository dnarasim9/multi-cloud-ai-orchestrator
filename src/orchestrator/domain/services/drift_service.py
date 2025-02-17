"""Domain service for drift detection operations."""

from __future__ import annotations

from typing import Any

import structlog

from orchestrator.domain.models.deployment import Deployment
from orchestrator.domain.models.drift import DriftReport
from orchestrator.domain.ports.repositories import (
    DeploymentRepository,
    DriftReportRepository,
)
from orchestrator.domain.ports.services import DriftDetector, EventPublisher


logger = structlog.get_logger(__name__)


class DriftDomainService:
    """Domain service for drift detection and remediation."""

    def __init__(
        self,
        deployment_repo: DeploymentRepository,
        drift_repo: DriftReportRepository,
        drift_detector: DriftDetector,
        event_publisher: EventPublisher,
    ) -> None:
        self._deployment_repo = deployment_repo
        self._drift_repo = drift_repo
        self._drift_detector = drift_detector
        self._event_publisher = event_publisher

    async def scan_deployment(self, deployment_id: str) -> DriftReport:
        """Scan a deployment for configuration drift."""
        deployment = await self._deployment_repo.get_by_id(deployment_id)
        if deployment is None:
            raise DriftScanError(f"Deployment {deployment_id} not found")

        expected_state = self._build_expected_state(deployment)
        report = await self._drift_detector.detect_drift(deployment_id, expected_state)
        report = await self._drift_repo.save(report)

        if report.has_drift:
            await self._event_publisher.publish(
                "drift.detected",
                {
                    "deployment_id": deployment_id,
                    "drift_count": len(report.items),
                    "max_severity": report.max_severity.value,
                },
            )

        logger.info(
            "drift_scan_completed",
            deployment_id=deployment_id,
            drift_found=report.has_drift,
            item_count=len(report.items),
        )
        return report

    def _build_expected_state(self, deployment: Deployment) -> dict[str, Any]:
        """Build expected state from deployment plan and results."""
        state: dict[str, Any] = {}
        if deployment.plan:
            for step in deployment.plan.steps:
                key = step.resource_spec.resource_identifier
                state[key] = step.resource_spec.model_dump()
        return state

    async def get_drift_history(
        self, deployment_id: str, limit: int = 20
    ) -> list[DriftReport]:
        """Get drift scan history for a deployment."""
        return await self._drift_repo.list_by_deployment(deployment_id, limit)


class DriftScanError(Exception):
    """Raised when a drift scan fails."""
