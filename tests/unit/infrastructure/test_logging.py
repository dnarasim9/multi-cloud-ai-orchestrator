"""Unit tests for logging configuration."""

from __future__ import annotations

from orchestrator.infrastructure.observability.logging import setup_logging


class TestLogging:
    def test_setup_logging_info(self) -> None:
        setup_logging("INFO")  # Should not raise

    def test_setup_logging_debug(self) -> None:
        setup_logging("DEBUG")  # Should not raise

    def test_setup_logging_warning(self) -> None:
        setup_logging("WARNING")  # Should not raise
