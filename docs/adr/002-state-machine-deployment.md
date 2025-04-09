# ADR-002: Explicit State Machine for Deployment Lifecycle

## Status
Accepted

## Context
Deployments go through a complex lifecycle with multiple states and valid transitions. We needed a way to enforce valid state transitions and prevent illegal operations.

## Decision
Implemented an explicit state machine with:
- 13 deployment states (PENDING through CANCELLED)
- Static transition map defining valid source→target pairs
- Transition validation in the aggregate root with descriptive errors
- Domain events emitted on significant transitions

## Alternatives Considered
- **Implicit State**: Track state via flags/booleans — error-prone, hard to reason about
- **State Pattern (GoF)**: Separate class per state — too much overhead for this use case
- **Workflow Engine**: External engine like Temporal — adds operational complexity

## Trade-offs
- (+) Compile-time visible transition rules
- (+) Easy to test every valid and invalid transition
- (+) Domain events provide audit trail
- (-) All transitions defined in one enum — could grow large
