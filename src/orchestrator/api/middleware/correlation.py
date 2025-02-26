"""Correlation ID middleware for request tracing."""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")

CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that adds correlation IDs to all requests."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = request.headers.get(
            CORRELATION_HEADER, str(uuid.uuid4())
        )
        correlation_id_ctx.set(correlation_id)

        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response


def get_correlation_id() -> str:
    """Get the current correlation ID."""
    return correlation_id_ctx.get()
