"""Unit tests for middleware components."""

from __future__ import annotations

from orchestrator.api.middleware.correlation import correlation_id_ctx, get_correlation_id


class TestCorrelationId:
    def test_default_empty(self) -> None:
        # Reset context
        token = correlation_id_ctx.set("")
        assert get_correlation_id() == ""
        correlation_id_ctx.reset(token)

    def test_set_and_get(self) -> None:
        token = correlation_id_ctx.set("test-correlation-123")
        assert get_correlation_id() == "test-correlation-123"
        correlation_id_ctx.reset(token)
