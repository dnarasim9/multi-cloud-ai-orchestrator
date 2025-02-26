"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import signal
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.api.middleware.correlation import CorrelationIdMiddleware
from orchestrator.api.middleware.rate_limiter import RateLimiterMiddleware
from orchestrator.api.routes import (
    auth_routes,
    deployment_routes,
    drift_routes,
    health_routes,
)
from orchestrator.config import get_settings, Settings


logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()
    logger.info(
        "application_starting",
        environment=settings.environment.value,
        debug=settings.debug,
    )

    # Graceful shutdown handler
    shutdown_event = asyncio.Event()

    def _signal_handler(sig: int, _frame: object) -> None:
        logger.info("shutdown_signal_received", signal=sig)
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    yield

    logger.info("application_shutting_down")
    # Cleanup resources
    logger.info("application_shutdown_complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Multi-Cloud Deployment Orchestrator",
        description="Multi-cloud deployment platform with autonomous orchestration",
        version="1.0.0",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # Middleware (order matters - first added = outermost)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(RateLimiterMiddleware, settings=settings.rate_limit)

    # Routes
    app.include_router(health_routes.router)
    app.include_router(auth_routes.router, prefix=settings.api_prefix)
    app.include_router(deployment_routes.router, prefix=settings.api_prefix)
    app.include_router(drift_routes.router, prefix=settings.api_prefix)

    return app
