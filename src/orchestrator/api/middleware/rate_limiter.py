"""Rate limiting middleware."""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from orchestrator.config import RateLimitSettings


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter middleware."""

    def __init__(self, app: ASGIApp, settings: RateLimitSettings | None = None) -> None:
        super().__init__(app)
        self._settings = settings or RateLimitSettings()
        self._buckets: dict[str, dict[str, float]] = defaultdict(
            lambda: {"tokens": float(self._settings.burst_size), "last_refill": time.time()}
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path.startswith("/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        bucket = self._buckets[client_ip]

        now = time.time()
        elapsed = now - bucket["last_refill"]
        refill_rate = self._settings.requests_per_minute / 60.0
        bucket["tokens"] = min(
            float(self._settings.burst_size),
            bucket["tokens"] + elapsed * refill_rate,
        )
        bucket["last_refill"] = now

        if bucket["tokens"] < 1.0:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry later."},
                headers={"Retry-After": str(int(60 / self._settings.requests_per_minute))},
            )

        bucket["tokens"] -= 1.0
        return await call_next(request)
