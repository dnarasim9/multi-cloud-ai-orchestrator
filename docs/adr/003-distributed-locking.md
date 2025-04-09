# ADR-003: Redis-Based Distributed Locking

## Status
Accepted

## Context
Concurrent deployment operations (planning, execution) must be serialized per deployment to prevent race conditions and inconsistent state.

## Decision
Redis SETNX-based distributed locks with:
- Unique lock values per acquisition for safe release
- Lua script atomic check-and-delete for release
- TTL-based expiration to prevent deadlocks
- Lock extension for long-running operations

## Alternatives Considered
- **PostgreSQL Advisory Locks**: Tied to database connections, harder to manage
- **Redlock (Multi-node)**: More complex, needed only for Redis cluster
- **ZooKeeper**: Heavy dependency for this use case

## Trade-offs
- (+) Simple implementation with Redis
- (+) Atomic operations via Lua scripts
- (+) TTL prevents deadlocks
- (-) Single Redis instance is a SPOF (mitigated by Redis Sentinel/Cluster in production)
