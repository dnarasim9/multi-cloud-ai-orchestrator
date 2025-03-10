"""Prometheus metrics configuration."""

from __future__ import annotations

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
)


# Application info
APP_INFO = Info("orchestrator", "Deployment Orchestrator application info")
APP_INFO.info({
    "version": "1.0.0",
    "service": "multi-cloud-deployment-orchestrator",
})

# Deployment metrics
DEPLOYMENTS_TOTAL = Counter(
    "orchestrator_deployments_total",
    "Total number of deployments",
    ["status", "environment", "provider"],
)

DEPLOYMENT_DURATION = Histogram(
    "orchestrator_deployment_duration_seconds",
    "Time taken for deployment execution",
    ["environment", "strategy"],
    buckets=[10, 30, 60, 120, 300, 600, 1800],
)

ACTIVE_DEPLOYMENTS = Gauge(
    "orchestrator_active_deployments",
    "Number of currently active deployments",
    ["status"],
)

# Task metrics
TASKS_TOTAL = Counter(
    "orchestrator_tasks_total",
    "Total number of tasks processed",
    ["status", "provider", "action"],
)

TASK_DURATION = Histogram(
    "orchestrator_task_duration_seconds",
    "Time taken for task execution",
    ["provider", "action"],
    buckets=[5, 10, 30, 60, 120, 300],
)

TASK_RETRIES = Counter(
    "orchestrator_task_retries_total",
    "Total number of task retries",
    ["provider"],
)

# Worker metrics
ACTIVE_WORKERS = Gauge(
    "orchestrator_active_workers",
    "Number of active worker agents",
)

WORKER_TASKS_IN_PROGRESS = Gauge(
    "orchestrator_worker_tasks_in_progress",
    "Number of tasks currently being processed by workers",
    ["worker_id"],
)

# Drift metrics
DRIFT_SCANS_TOTAL = Counter(
    "orchestrator_drift_scans_total",
    "Total number of drift scans",
    ["result"],  # "clean", "drift_detected"
)

DRIFT_ITEMS_FOUND = Counter(
    "orchestrator_drift_items_found_total",
    "Total number of drift items found",
    ["severity"],
)

# API metrics
API_REQUESTS_TOTAL = Counter(
    "orchestrator_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)

API_REQUEST_DURATION = Histogram(
    "orchestrator_api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Infrastructure metrics
DB_QUERY_DURATION = Histogram(
    "orchestrator_db_query_duration_seconds",
    "Database query duration",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

REDIS_OPERATIONS_TOTAL = Counter(
    "orchestrator_redis_operations_total",
    "Total Redis operations",
    ["operation", "result"],
)

DISTRIBUTED_LOCK_OPERATIONS = Counter(
    "orchestrator_distributed_lock_operations_total",
    "Total distributed lock operations",
    ["operation", "result"],  # operation: acquire/release, result: success/failure
)
