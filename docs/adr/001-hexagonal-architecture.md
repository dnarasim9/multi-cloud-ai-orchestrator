# ADR-001: Hexagonal Architecture

## Status
Accepted

## Context
We needed an architecture that cleanly separates business logic from infrastructure concerns, enables testability, and supports swapping infrastructure components (e.g., switching from PostgreSQL to DynamoDB, or from simulated Terraform to real Terraform).

## Decision
Adopted hexagonal (ports and adapters) architecture with four layers:
- **Domain Layer**: Core business logic, entities, value objects, domain events, and port interfaces
- **Application Layer**: Orchestrates domain operations, handles cross-cutting concerns
- **Infrastructure Layer**: Implements ports with concrete adapters (PostgreSQL, Redis, Kafka, Terraform)
- **API Layer**: HTTP interface via FastAPI

## Alternatives Considered
- **Layered Architecture**: Simpler but creates tight coupling between layers
- **CQRS/Event Sourcing**: More complex than needed for initial implementation
- **Microservices**: Premature at current scale; monolith-first approach preferred

## Trade-offs
- (+) Domain layer has zero external dependencies
- (+) Easy to test with in-memory implementations
- (+) Infrastructure components are swappable
- (-) More boilerplate (port interfaces + implementations)
- (-) Learning curve for developers unfamiliar with the pattern
