# Deployment Guide

This guide covers how to build, deploy, and test the Multi-Cloud Autonomous Deployment Orchestrator in local development, Docker Compose, and Kubernetes environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Running the API Server](#running-the-api-server)
4. [Docker Compose Deployment](#docker-compose-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Running the Test Suite](#running-the-test-suite)
7. [API Usage Examples](#api-usage-examples)
8. [Environment Configuration Reference](#environment-configuration-reference)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool | Minimum Version | Required For |
|------|----------------|--------------|
| Python | 3.10+ | All local usage |
| pip | 22.0+ | Package installation |
| Docker | 20.10+ | Containerized deployment |
| Docker Compose | 2.0+ | Multi-service local stack |
| kubectl | 1.27+ | Kubernetes deployment |
| Helm | 3.0+ | Kubernetes (optional) |
| Git | 2.30+ | Source control |

---

## Local Development Setup

### 1. Clone and enter the repository

```bash
git clone https://github.com/dnarasim9/multi-cloud-ai-orchestrator.git
cd multi-cloud-ai-orchestrator
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# or
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

**Option A: Using requirements files (recommended for most setups)**

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install dev/test dependencies
pip install -r requirements-dev.txt
```

**Option B: Using pyproject.toml with editable install**

```bash
# Install the package in editable mode with dev extras
pip install -e ".[dev]"
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your local settings (defaults work for local dev)
```

The application ships with sensible defaults for local development. The in-memory repositories are used by default, so PostgreSQL, Redis, and Kafka are **optional** for basic API testing.

### 5. Set the Python path

```bash
export PYTHONPATH=$(pwd)/src
```

---

## Running the API Server

### Direct invocation (development)

```bash
# From the project root, with PYTHONPATH set:
python -m orchestrator.main
```

The server starts on `http://localhost:8000` by default.

### Using uvicorn directly (with hot-reload)

```bash
uvicorn orchestrator.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

### Verify the server is running

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"2025-...","version":"1.0.0"}

# OpenAPI docs (interactive)
open http://localhost:8000/docs
```

---

## Docker Compose Deployment

Docker Compose brings up the full stack: the orchestrator API, PostgreSQL, Redis, Kafka, and Prometheus.

### 1. Build and start all services

```bash
docker compose up --build -d
```

### 2. Verify services are healthy

```bash
docker compose ps
```

All services should show `healthy` or `running` status. The orchestrator waits for PostgreSQL and Redis health checks before starting.

### 3. Access the services

| Service | URL | Description |
|---------|-----|-------------|
| Orchestrator API | http://localhost:8000 | Main REST API |
| Swagger Docs | http://localhost:8000/docs | Interactive API docs |
| PostgreSQL | localhost:5432 | Database (user: `orchestrator`, pass: `orchestrator_pass`) |
| Redis | localhost:6379 | Cache / distributed locks |
| Kafka | localhost:9092 | Event streaming (disabled by default) |
| Prometheus | http://localhost:9090 | Metrics dashboard |

### 4. View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f orchestrator
```

### 5. Stop and clean up

```bash
# Stop services (preserves data volumes)
docker compose down

# Stop and remove all data
docker compose down -v
```

---

## Kubernetes Deployment

Manifests are provided in `deploy/kubernetes/`.

### 1. Create the namespace

```bash
kubectl apply -f deploy/kubernetes/namespace.yaml
```

### 2. Apply secrets and configuration

```bash
# Edit secrets first (base64-encode values)
kubectl apply -f deploy/kubernetes/secrets.yaml
kubectl apply -f deploy/kubernetes/configmap.yaml
```

### 3. Deploy the application

```bash
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl apply -f deploy/kubernetes/service.yaml
kubectl apply -f deploy/kubernetes/hpa.yaml
```

### 4. Verify the deployment

```bash
kubectl -n deployment-orchestrator get pods
kubectl -n deployment-orchestrator get svc

# Check logs
kubectl -n deployment-orchestrator logs -l app=orchestrator -f
```

### 5. Port-forward for local access

```bash
kubectl -n deployment-orchestrator port-forward svc/orchestrator 8000:8000
```

The API is now available at `http://localhost:8000`.

---

## Running the Test Suite

### Run all tests with coverage

```bash
pytest
```

This uses the configuration in `pyproject.toml` which includes verbose output, coverage reporting, and term-missing details. The minimum coverage threshold is 80%.

### Run specific test categories

```bash
# Unit tests only
pytest tests/unit/

# Domain model tests
pytest tests/unit/domain/

# Infrastructure tests
pytest tests/unit/infrastructure/

# API schema tests
pytest tests/unit/api/

# Worker tests
pytest tests/unit/workers/

# Application service tests
pytest tests/unit/application/
```

### Run a single test file

```bash
pytest tests/unit/domain/test_deployment.py -v
```

### Generate HTML coverage report

```bash
pytest --cov-report=html
# Open htmlcov/index.html in your browser
```

### Linting and static analysis

```bash
# Ruff linter
ruff check src/ tests/

# Type checking
mypy src/orchestrator

# Security scan
bandit -r src/orchestrator

# Cyclomatic complexity
radon cc src/orchestrator -a -nc
```

---

## API Usage Examples

Below is a complete walkthrough of the deployment lifecycle using `curl`. All examples assume the server is running at `http://localhost:8000`.

### Step 1: Register a user

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "SecurePass123!",
    "role": "admin",
    "tenant_id": "tenant-001"
  }' | python -m json.tool
```

### Step 2: Login to get a JWT token

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "SecurePass123!"
  }' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
```

### Step 3: Verify authentication

```bash
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

### Step 4: Create a deployment

```bash
DEPLOYMENT=$(curl -s -X POST http://localhost:8000/api/v1/deployments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Deploy web application to AWS and GCP",
    "target_providers": ["aws", "gcp"],
    "target_regions": ["us-east-1", "us-central1"],
    "resources": [
      {
        "resource_type": "compute",
        "provider": "aws",
        "region": "us-east-1",
        "name": "web-server",
        "properties": {"instance_type": "t3.large"}
      },
      {
        "resource_type": "database",
        "provider": "gcp",
        "region": "us-central1",
        "name": "app-db",
        "properties": {"engine": "postgres", "version": "16"}
      }
    ],
    "strategy": "blue_green",
    "environment": "staging",
    "auto_approve": false,
    "rollback_on_failure": true
  }')

echo "$DEPLOYMENT" | python -m json.tool

# Extract the deployment ID
DEPLOY_ID=$(echo "$DEPLOYMENT" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Deployment ID: $DEPLOY_ID"
```

### Step 5: Generate an execution plan

```bash
curl -s -X POST "http://localhost:8000/api/v1/deployments/$DEPLOY_ID/plan" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

The response includes the generated execution plan with steps, estimated durations, risk assessment, and reasoning.

### Step 6: Approve the deployment

```bash
curl -s -X POST "http://localhost:8000/api/v1/deployments/$DEPLOY_ID/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "admin"}' | python -m json.tool
```

### Step 7: Execute the deployment

```bash
curl -s -X POST "http://localhost:8000/api/v1/deployments/$DEPLOY_ID/execute" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

This creates tasks for each execution step and returns the number of tasks created.

### Step 8: Rollback (if needed)

```bash
curl -s -X POST "http://localhost:8000/api/v1/deployments/$DEPLOY_ID/rollback" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

### Step 9: Drift detection scan

```bash
curl -s -X POST http://localhost:8000/api/v1/drift/scan \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"deployment_id\": \"$DEPLOY_ID\"}" | python -m json.tool
```

### Health check endpoints

```bash
# Basic health
curl -s http://localhost:8000/health | python -m json.tool

# Readiness (dependency checks)
curl -s http://localhost:8000/health/ready | python -m json.tool

# Liveness
curl -s http://localhost:8000/health/live | python -m json.tool
```

---

## Environment Configuration Reference

All configuration is driven by environment variables. Copy `.env.example` to `.env` and adjust as needed.

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Runtime environment (`development`, `staging`, `production`) |
| `DEBUG` | `false` | Enable debug mode |
| `API_PREFIX` | `/api/v1` | API route prefix |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `WORKERS` | `1` | Number of uvicorn workers |

### Database (PostgreSQL)

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `orchestrator` | Database name |
| `DB_USER` | `orchestrator` | Database user |
| `DB_PASSWORD` | `orchestrator_pass` | Database password |
| `DB_POOL_SIZE` | `20` | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | *(empty)* | Redis password |
| `REDIS_DB` | `0` | Redis database number |

### Kafka

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker addresses |
| `KAFKA_ENABLED` | `false` | Enable Kafka event publishing |
| `KAFKA_TOPIC_PREFIX` | `orchestrator` | Topic name prefix |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_SECRET_KEY` | `change-me-in-production` | JWT signing secret (**change in production**) |
| `AUTH_ALGORITHM` | `HS256` | JWT algorithm |
| `AUTH_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL in minutes |

### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `OTLP_ENDPOINT` | `http://localhost:4317` | OpenTelemetry collector endpoint |
| `SERVICE_NAME` | `deployment-orchestrator` | Service name for tracing |
| `LOG_LEVEL` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics |
| `TRACING_ENABLED` | `true` | Enable OpenTelemetry tracing |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_RPM` | `60` | Requests per minute limit |
| `RATE_LIMIT_BURST` | `10` | Burst capacity |

---

## Troubleshooting

### Server won't start

Make sure `PYTHONPATH` includes the `src/` directory:

```bash
export PYTHONPATH=$(pwd)/src
```

### Import errors after pip install

If you installed via `pip install -e ".[dev]"` but still get import errors, verify the package is installed:

```bash
pip show multi-cloud-deployment-orchestrator
```

### Docker Compose services unhealthy

PostgreSQL and Redis have health checks configured. If the orchestrator fails to start, check the dependency service logs:

```bash
docker compose logs postgres
docker compose logs redis
```

### Tests fail with coverage below 80%

The coverage configuration in `pyproject.toml` excludes files that require external services (PostgreSQL repositories, DB models, tracing, metrics). If coverage drops below 80%, add tests for newly added code and check which files are contributing to the gap:

```bash
pytest --cov-report=html
# Then inspect htmlcov/index.html
```

### JWT token expired

The default access token TTL is 30 minutes. Re-login to get a fresh token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "SecurePass123!"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Permission denied (403 Forbidden)

Different roles have different permissions. The `admin` role has full access. Other roles (`operator`, `developer`, `viewer`) have restricted permissions. Check the RBAC mapping in `src/orchestrator/domain/models/user.py`.
