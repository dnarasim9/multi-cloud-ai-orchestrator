# Multi-Cloud Autonomous Deployment Orchestrator

A multi-cloud deployment platform that provides autonomous infrastructure orchestration with intelligent planning, drift detection, and rollback capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          API Layer (FastAPI)                        │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐  │
│  │   Auth   │  │ Deployments  │  │  Drift   │  │   Health     │  │
│  │  Routes  │  │   Routes     │  │  Routes  │  │   Routes     │  │
│  └──────────┘  └──────────────┘  └──────────┘  └──────────────┘  │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐   │
│  │    Middleware         │  │        Dependencies (DI)         │   │
│  │ • Correlation ID     │  │ • Auth guards                    │   │
│  │ • Rate Limiting      │  │ • Service container              │   │
│  └──────────────────────┘  └──────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                      Domain Layer (Core)                            │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   Aggregates     │  │   Ports      │  │  Domain Services     │ │
│  │ • Deployment     │  │ • Repos      │  │ • DeploymentService  │ │
│  │ • Task           │  │ • Services   │  │ • DriftService       │ │
│  │ • DriftReport    │  │              │  │                      │ │
│  │ • User           │  │              │  │                      │ │
│  └──────────────────┘  └──────────────┘  └──────────────────────┘ │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐   │
│  │  Value Objects    │  │         Domain Events                │   │
│  │ • ResourceSpec   │  │ • DeploymentCreated/Completed/Failed │   │
│  │ • ExecutionPlan  │  │ • PlanGenerated, RollbackStarted     │   │
│  │ • CloudRegion    │  │                                      │   │
│  └──────────────────┘  └──────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                              │
│  ┌────────────┐ ┌────────────┐ ┌────────┐ ┌──────────────────────┐│
│  │ PostgreSQL │ │   Redis    │ │ Kafka  │ │     Terraform        ││
│  │   Repos    │ │ Cache/Lock │ │ Events │ │     Executor         ││
│  └────────────┘ └────────────┘ └────────┘ └──────────────────────┘│
│  ┌────────────┐ ┌────────────┐ ┌──────────────────────────────┐   │
│  │  Planning  │ │   Drift    │ │       Observability          │   │
│  │  Engine    │ │  Detector  │ │ • Structured Logging         │   │
│  └────────────┘ └────────────┘ │ • Prometheus Metrics         │   │
│                                 │ • OpenTelemetry Tracing      │   │
│                                 └──────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                        Worker Agents                                │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Terraform Worker │  │ HealthCheck      │  │  Base Worker    │  │
│  │ (plan/apply)     │  │ Worker           │  │  (Template)     │  │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Features

**Intelligent Planning** — Submit deployment intent via REST API; the planning engine generates optimized execution plans with dependency resolution, cost estimation, and risk assessment.

**Multi-Cloud Abstraction** — Unified interface for AWS, Azure, and GCP with provider-specific Terraform configuration generation. Resource types include compute, storage, database, network, containers, serverless, and more.

**Full State Machine** — 13-state deployment lifecycle (PENDING → PLANNING → PLANNED → AWAITING_APPROVAL → APPROVED → EXECUTING → VERIFYING → COMPLETED) with rollback and cancellation paths. 9-state task lifecycle with retry support.

**Agent-Based Execution** — Worker agents poll for tasks, execute Terraform operations, and report results. Supports concurrent execution with configurable parallelism and timeout handling.

**Drift Detection** — Compares expected infrastructure state against actual cloud state. Generates drift reports with severity classification (LOW/MEDIUM/HIGH/CRITICAL).

**Rollback Support** — Automatic rollback on failure with configurable rollback policies. Maintains full execution history for auditability.

**Distributed Locking** — Redis-based distributed locks with Lua script atomic operations for safe concurrent deployment orchestration.

**Idempotent Execution** — Every task carries an idempotency key to ensure safe retry behavior.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (async) |
| Language | Python 3.10+ |
| Database | PostgreSQL 16 (async via asyncpg) |
| Cache/Locks | Redis 7 |
| Messaging | Apache Kafka (optional) |
| IaC | Terraform (simulated) |
| Auth | JWT (HS256) with RBAC |
| Logging | structlog (JSON) |
| Metrics | Prometheus |
| Tracing | OpenTelemetry |
| Container | Docker multi-stage |
| Orchestration | Kubernetes + HPA |
| CI/CD | GitHub Actions |

## Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- PostgreSQL 16, Redis 7 (optional for local dev)

### Local Development

```bash
# Clone and setup
git clone https://github.com/dnarasim9/multi-cloud-ai-orchestrator.git
cd multi-cloud-ai-orchestrator
cp .env.example .env

# Install dependencies
pip install -e ".[dev]"

# Start infrastructure
docker-compose up -d postgres redis

# Run the server
PYTHONPATH=src python -m orchestrator.main

# Run tests
pytest tests/ -v --cov
```

### Docker Compose (Full Stack)

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000/api/v1/docs`.

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Authenticate and get JWT |
| GET | `/api/v1/auth/me` | Get current user info |

### Deployments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/deployments` | Create deployment from intent |
| POST | `/api/v1/deployments/{id}/plan` | Generate execution plan |
| POST | `/api/v1/deployments/{id}/approve` | Approve deployment |
| POST | `/api/v1/deployments/{id}/execute` | Start execution |
| POST | `/api/v1/deployments/{id}/rollback` | Rollback deployment |

### Drift Detection
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/drift/scan` | Trigger drift scan |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/ready` | Readiness probe |
| GET | `/health/live` | Liveness probe |

## Deployment Lifecycle Sequence

```
Client                API              DomainService        PlanningEngine        Worker
  │                    │                    │                     │                  │
  │  POST /deploy      │                    │                     │                  │
  │───────────────────>│  create_deployment  │                     │                  │
  │                    │───────────────────>│                     │                  │
  │  201 Created       │                    │                     │                  │
  │<───────────────────│                    │                     │                  │
  │                    │                    │                     │                  │
  │  POST /plan        │                    │                     │                  │
  │───────────────────>│  plan_deployment   │                     │                  │
  │                    │───────────────────>│  generate_plan      │                  │
  │                    │                    │────────────────────>│                  │
  │                    │                    │  ExecutionPlan      │                  │
  │                    │                    │<────────────────────│                  │
  │  200 Planned       │                    │                     │                  │
  │<───────────────────│                    │                     │                  │
  │                    │                    │                     │                  │
  │  POST /approve     │                    │                     │                  │
  │───────────────────>│  approve           │                     │                  │
  │                    │───────────────────>│                     │                  │
  │  200 Approved      │                    │                     │                  │
  │<───────────────────│                    │                     │                  │
  │                    │                    │                     │                  │
  │  POST /execute     │                    │                     │                  │
  │───────────────────>│  execute           │                     │  poll for tasks  │
  │                    │───────────────────>│  create tasks       │────────────────>│
  │  200 Executing     │                    │                     │  acquire task   │
  │<───────────────────│                    │                     │  tf plan/apply  │
  │                    │                    │                     │  report result  │
  │                    │                    │<────────────────────────────────────── │
  │                    │                    │  verify & complete  │                  │
```

## Design Patterns Used

- **State Machine** — Deployment and Task lifecycle management
- **Repository** — Data access abstraction (PostgreSQL, In-Memory implementations)
- **Strategy** — Planning engine with pluggable strategies
- **Template Method** — WorkerAgent base class with execute() hook
- **Factory** — Service container for dependency assembly
- **Observer** — Domain events with publish/subscribe
- **Adapter** — Cloud provider abstraction
- **Builder** — Execution plan construction
- **Command** — Task-based execution model
- **Value Object** — Immutable domain primitives
- **Aggregate Root** — Transaction boundaries with event collection

## Design Trade-offs

1. **In-Memory vs External Planning** — Used a rule-based planning engine instead of LLM integration. This provides deterministic, testable behavior while maintaining the same interface for future LLM integration.

2. **Simulated Terraform** — Terraform operations are simulated to enable development and testing without cloud credentials. The `TerraformExecutor` port allows swapping in real implementations.

3. **Event-Driven vs Request-Response** — Used event publishing for decoupled communication between aggregates while maintaining synchronous API responses for client simplicity.

4. **Module-Level Stores** — In-memory repositories use module-level shared dictionaries for cross-instance sharing in the demo API. Production uses PostgreSQL with proper session management.

## Scaling Considerations

- **Horizontal Scaling**: API layer scales via K8s HPA based on CPU/memory. Stateless design with external state in PostgreSQL/Redis.
- **Worker Scaling**: Worker agents can be independently scaled. Task queue in PostgreSQL with `SELECT FOR UPDATE SKIP LOCKED` ensures safe concurrent acquisition.
- **Database**: Connection pooling (20 connections + 10 overflow), composite indexes on hot query paths.
- **Caching**: Redis caching layer for frequently-accessed deployment state.
- **Rate Limiting**: Token bucket algorithm at API gateway level.

## Failure Handling

- **Retry with Backoff**: Tasks retry up to 3 times with tracking
- **Circuit Breaker**: Available via `circuitbreaker` library integration
- **Distributed Locks**: Redis locks with TTL prevent concurrent modifications
- **Graceful Shutdown**: SIGTERM handling with in-flight request draining
- **Idempotency**: Every task has a unique idempotency key for safe replays
- **Rollback**: Automatic rollback on deployment failure when configured

## Project Structure

```
├── src/orchestrator/
│   ├── domain/          # Core business logic (no external deps)
│   │   ├── models/      # Entities, Value Objects, Aggregates
│   │   ├── events/      # Domain events
│   │   ├── ports/       # Interfaces (Repository, Service ports)
│   │   └── services/    # Domain services
│   ├── infrastructure/  # External system adapters
│   │   ├── persistence/ # PostgreSQL repos, ORM models
│   │   ├── cache/       # Redis cache and distributed locks
│   │   ├── messaging/   # Event publishing (In-Memory, Kafka)
│   │   ├── terraform/   # Terraform execution
│   │   ├── ai/          # Planning engine, drift detection
│   │   ├── auth/        # JWT authentication
│   │   └── observability/ # Logging, metrics, tracing
│   ├── api/             # FastAPI routes, middleware, schemas
│   ├── workers/         # Agent-based task execution
│   └── config.py        # Application configuration
├── tests/               # Unit, integration, API tests
├── deploy/              # Docker, Kubernetes, Helm configs
├── docs/adr/            # Architecture Decision Records
└── .github/workflows/   # CI/CD pipeline
```

## Running Tests

```bash
# All tests
pytest tests/ -v --cov

# Unit tests only
pytest tests/unit/ -v

# With coverage report
pytest tests/ --cov=src/orchestrator --cov-report=html
```

