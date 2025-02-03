# Multi-Cloud Autonomous Deployment Orchestrator

An autonomous multi-cloud deployment orchestrator built with hexagonal architecture, featuring AI-driven planning, drift detection, and self-healing infrastructure management.

## Architecture

This project follows hexagonal (ports & adapters) architecture with clear separation between:
- **Domain Layer**: Core business logic and entities
- **Application Layer**: Use cases and service orchestration
- **Infrastructure Layer**: External adapters (Terraform, databases, messaging)
- **API Layer**: FastAPI REST endpoints

## Getting Started

```bash
pip install -e ".[dev]"
pytest
```
