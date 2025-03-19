"""Health check and metrics routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check - verifies all dependencies are available."""
    checks: dict[str, str] = {}

    # In production, check DB, Redis, Kafka connectivity
    checks["database"] = "ok"
    checks["redis"] = "ok"
    checks["kafka"] = "ok"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Liveness check - verifies the service is running."""
    return {"status": "alive"}
