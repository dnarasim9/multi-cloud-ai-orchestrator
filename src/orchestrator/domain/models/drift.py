"""Drift detection domain models."""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from orchestrator.domain.models.base import AggregateRoot, ValueObject


class DriftSeverity(str, Enum):
    """Severity level of detected drift."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DriftType(str, Enum):
    """Type of configuration drift."""

    PROPERTY_CHANGED = "property_changed"
    RESOURCE_ADDED = "resource_added"
    RESOURCE_REMOVED = "resource_removed"
    STATE_MISMATCH = "state_mismatch"
    TAG_MISMATCH = "tag_mismatch"


class DriftItem(ValueObject):
    """Individual drift finding."""

    drift_type: DriftType
    resource_identifier: str
    property_path: str = ""
    expected_value: str = ""
    actual_value: str = ""
    severity: DriftSeverity = DriftSeverity.MEDIUM


class DriftReport(AggregateRoot):
    """Drift detection report aggregate."""

    deployment_id: str
    scan_type: str = "scheduled"
    items: list[DriftItem] = Field(default_factory=list)
    summary: str = ""
    auto_remediate: bool = False
    remediation_deployment_id: str | None = None

    @property
    def has_drift(self) -> bool:
        return len(self.items) > 0

    @property
    def critical_count(self) -> int:
        return sum(1 for item in self.items if item.severity == DriftSeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for item in self.items if item.severity == DriftSeverity.HIGH)

    @property
    def max_severity(self) -> DriftSeverity:
        if not self.items:
            return DriftSeverity.LOW
        severity_order = [
            DriftSeverity.CRITICAL, DriftSeverity.HIGH,
            DriftSeverity.MEDIUM, DriftSeverity.LOW,
        ]
        for severity in severity_order:
            if any(item.severity == severity for item in self.items):
                return severity
        return DriftSeverity.LOW
