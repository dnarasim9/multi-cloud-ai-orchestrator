# ADR-004: Agent-Based Task Execution Model

## Status
Accepted

## Context
Deployment plans consist of multiple steps that may run in parallel or sequentially. We needed a scalable execution model that supports concurrent processing, failure handling, and retries.

## Decision
Adopted an agent-based execution model:
- **WorkerAgent** base class with Template Method pattern
- Workers poll for tasks using `SELECT FOR UPDATE SKIP LOCKED` for safe concurrent acquisition
- Each task has its own lifecycle state machine with retry support
- Configurable concurrency per worker via semaphores
- Timeout handling via asyncio.wait_for

## Alternatives Considered
- **Celery**: Heavy dependency, complex configuration
- **asyncio.gather**: Simple but lacks persistence and retry
- **Temporal/Cadence**: Full workflow engine — too heavy for MVP

## Trade-offs
- (+) Simple, testable worker model
- (+) Horizontal scaling by adding more workers
- (+) Database-backed task queue ensures durability
- (-) Polling introduces latency (mitigated by short poll intervals)
- (-) No built-in workflow orchestration (manual dependency handling)
