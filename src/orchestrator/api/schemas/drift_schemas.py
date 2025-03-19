"""API schemas for drift detection endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from orchestrator.domain.models.drift import DriftSeverity, DriftType


class DriftItemResponse(BaseModel):
    drift_type: DriftType
    resource_identifier: str
    property_path: str = ""
    expected_value: str = ""
    actual_value: str = ""
    severity: DriftSeverity


class DriftReportResponse(BaseModel):
    id: str
    deployment_id: str
    scan_type: str
    items: list[DriftItemResponse] = Field(default_factory=list)
    summary: str = ""
    has_drift: bool
    critical_count: int
    high_count: int
    max_severity: DriftSeverity
    created_at: datetime


class ScanDriftRequest(BaseModel):
    deployment_id: str
    auto_remediate: bool = False
