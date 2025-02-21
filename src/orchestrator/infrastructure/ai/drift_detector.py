"""Drift detection implementation."""

from __future__ import annotations

import random
from typing import Any

import structlog

from orchestrator.domain.models.cloud_provider import CloudProviderType
from orchestrator.domain.models.drift import (
    DriftItem,
    DriftReport,
    DriftSeverity,
    DriftType,
)
from orchestrator.domain.ports.services import DriftDetector


logger = structlog.get_logger(__name__)


class SimulatedDriftDetector(DriftDetector):
    """Simulated drift detector for development/testing.

    Compares expected state against simulated 'actual' state
    and generates drift reports.
    """

    def __init__(self, drift_probability: float = 0.3) -> None:
        self._drift_probability = drift_probability
        self._simulated_states: dict[str, dict[str, Any]] = {}

    async def detect_drift(
        self, deployment_id: str, expected_state: dict[str, Any]
    ) -> DriftReport:
        """Detect drift by comparing expected vs actual state."""
        logger.info("drift_detection_started", deployment_id=deployment_id)

        actual_state = await self.get_current_state(
            CloudProviderType.AWS, list(expected_state)
        )

        items: list[DriftItem] = []
        for resource_id in expected_state:
            actual = actual_state.get(resource_id, {})

            if not actual:
                items.append(DriftItem(
                    drift_type=DriftType.RESOURCE_REMOVED,
                    resource_identifier=resource_id,
                    severity=DriftSeverity.CRITICAL,
                ))
                continue

            if random.random() < self._drift_probability:  # noqa: S311
                items.append(DriftItem(
                    drift_type=DriftType.PROPERTY_CHANGED,
                    resource_identifier=resource_id,
                    property_path="properties.instance_type",
                    expected_value="t3.medium",
                    actual_value="t3.large",
                    severity=DriftSeverity.MEDIUM,
                ))

        report = DriftReport(
            deployment_id=deployment_id,
            items=items,
            summary=f"Found {len(items)} drift items" if items else "No drift detected",
        )

        logger.info(
            "drift_detection_completed",
            deployment_id=deployment_id,
            drift_count=len(items),
        )
        return report

    async def get_current_state(
        self, provider: CloudProviderType, resource_ids: list[str]
    ) -> dict[str, Any]:
        """Get simulated current state."""
        state: dict[str, Any] = {}
        for resource_id in resource_ids:
            if resource_id in self._simulated_states:
                state[resource_id] = self._simulated_states[resource_id]
            else:
                state[resource_id] = {"status": "running", "provider": provider.value}
        return state

    def set_simulated_state(self, resource_id: str, state: dict[str, Any]) -> None:
        """Set simulated state for testing."""
        self._simulated_states[resource_id] = state
