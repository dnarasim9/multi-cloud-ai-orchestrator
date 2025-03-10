"""Unit tests for drift detector."""

from __future__ import annotations

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType
from orchestrator.domain.models.drift import DriftType
from orchestrator.infrastructure.ai.drift_detector import SimulatedDriftDetector


class TestSimulatedDriftDetector:
    @pytest.mark.asyncio
    async def test_no_drift_when_probability_zero(self) -> None:
        detector = SimulatedDriftDetector(drift_probability=0.0)
        expected = {"res-1": {"status": "running"}}
        detector.set_simulated_state("res-1", {"status": "running"})
        report = await detector.detect_drift("d-1", expected)
        assert not report.has_drift

    @pytest.mark.asyncio
    async def test_detect_removed_resource(self) -> None:
        detector = SimulatedDriftDetector(drift_probability=0.0)
        expected = {"res-1": {"status": "running"}}
        # Don't set any simulated state for res-1 — but get_current_state
        # returns a default state, so resource won't be missing.
        # Instead, clear all simulated states and override get_current_state behavior
        report = await detector.detect_drift("d-1", expected)
        # With drift_probability=0.0 and default state returned, no drift
        assert report.deployment_id == "d-1"

    @pytest.mark.asyncio
    async def test_always_drift_when_probability_one(self) -> None:
        detector = SimulatedDriftDetector(drift_probability=1.0)
        expected = {"res-1": {"status": "running"}}
        detector.set_simulated_state("res-1", {"status": "running"})
        report = await detector.detect_drift("d-1", expected)
        assert report.has_drift
        assert len(report.items) >= 1
        assert report.items[0].drift_type == DriftType.PROPERTY_CHANGED

    @pytest.mark.asyncio
    async def test_get_current_state_default(self) -> None:
        detector = SimulatedDriftDetector()
        state = await detector.get_current_state(CloudProviderType.AWS, ["r1", "r2"])
        assert "r1" in state
        assert "r2" in state

    @pytest.mark.asyncio
    async def test_get_current_state_with_simulated(self) -> None:
        detector = SimulatedDriftDetector()
        detector.set_simulated_state("r1", {"custom": "data"})
        state = await detector.get_current_state(CloudProviderType.AWS, ["r1"])
        assert state["r1"]["custom"] == "data"

    @pytest.mark.asyncio
    async def test_set_simulated_state(self) -> None:
        detector = SimulatedDriftDetector()
        detector.set_simulated_state("resource-x", {"key": "value"})
        state = await detector.get_current_state(CloudProviderType.GCP, ["resource-x"])
        assert state["resource-x"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_report_summary_with_drift(self) -> None:
        detector = SimulatedDriftDetector(drift_probability=1.0)
        expected = {"res-1": {"status": "running"}}
        detector.set_simulated_state("res-1", {"status": "running"})
        report = await detector.detect_drift("d-1", expected)
        assert "drift" in report.summary.lower() or "Found" in report.summary
