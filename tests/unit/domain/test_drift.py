"""Unit tests for drift detection domain model."""

from __future__ import annotations

from orchestrator.domain.models.drift import (
    DriftItem,
    DriftReport,
    DriftSeverity,
    DriftType,
)


class TestDriftReport:
    def test_no_drift(self) -> None:
        report = DriftReport(deployment_id="d-1")
        assert not report.has_drift
        assert report.critical_count == 0
        assert report.max_severity == DriftSeverity.LOW

    def test_with_drift_items(self) -> None:
        items = [
            DriftItem(
                drift_type=DriftType.PROPERTY_CHANGED,
                resource_identifier="aws/us-east-1/compute/test",
                severity=DriftSeverity.MEDIUM,
            ),
            DriftItem(
                drift_type=DriftType.RESOURCE_REMOVED,
                resource_identifier="aws/us-east-1/storage/bucket",
                severity=DriftSeverity.CRITICAL,
            ),
        ]
        report = DriftReport(deployment_id="d-1", items=items)
        assert report.has_drift
        assert report.critical_count == 1
        assert report.high_count == 0
        assert report.max_severity == DriftSeverity.CRITICAL

    def test_high_severity(self) -> None:
        items = [
            DriftItem(
                drift_type=DriftType.STATE_MISMATCH,
                resource_identifier="gcp/us-central1/db/main",
                severity=DriftSeverity.HIGH,
            ),
        ]
        report = DriftReport(deployment_id="d-1", items=items)
        assert report.max_severity == DriftSeverity.HIGH
        assert report.high_count == 1
