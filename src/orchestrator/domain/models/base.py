"""Base domain model classes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class DomainEntity(BaseModel):
    """Base class for all domain entities."""

    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    version: int = Field(default=1)

    def touch(self) -> None:
        """Update the timestamp and increment version."""
        self.updated_at = utc_now()
        self.version += 1

    model_config = {"frozen": False, "validate_assignment": True}


class ValueObject(BaseModel):
    """Base class for value objects (immutable)."""

    model_config = {"frozen": True}


class AggregateRoot(DomainEntity):
    """Base class for aggregate roots that emit domain events."""

    _domain_events: list[DomainEvent] = []

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        object.__setattr__(self, "_domain_events", [])

    def add_event(self, event: DomainEvent) -> None:
        """Register a domain event."""
        self._domain_events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Collect and clear all pending domain events."""
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    @property
    def pending_events(self) -> list[DomainEvent]:
        """Get pending domain events without clearing."""
        return list(self._domain_events)


class DomainEvent(BaseModel):
    """Base class for domain events."""

    event_id: str = Field(default_factory=generate_id)
    event_type: str = ""
    occurred_at: datetime = Field(default_factory=utc_now)
    correlation_id: str = Field(default_factory=generate_id)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}
