"""Unit tests for base domain models."""

from __future__ import annotations

from orchestrator.domain.models.base import (
    AggregateRoot,
    DomainEntity,
    DomainEvent,
    generate_id,
    utc_now,
    ValueObject,
)


class TestGenerateId:
    def test_returns_string(self) -> None:
        assert isinstance(generate_id(), str)

    def test_unique(self) -> None:
        ids = {generate_id() for _ in range(100)}
        assert len(ids) == 100


class TestUtcNow:
    def test_returns_datetime(self) -> None:
        now = utc_now()
        assert now.tzinfo is not None


class TestDomainEntity:
    def test_defaults(self) -> None:
        entity = DomainEntity()
        assert entity.version == 1
        assert entity.id is not None
        assert entity.created_at is not None

    def test_touch(self) -> None:
        entity = DomainEntity()
        v = entity.version
        entity.touch()
        assert entity.version == v + 1


class TestValueObject:
    def test_immutable(self) -> None:
        class Price(ValueObject):
            amount: float
            currency: str

        p = Price(amount=9.99, currency="USD")
        assert p.amount == 9.99
        # ValueObjects are frozen


class TestDomainEvent:
    def test_defaults(self) -> None:
        event = DomainEvent()
        assert event.event_id is not None
        assert event.occurred_at is not None

    def test_custom_type(self) -> None:
        event = DomainEvent(event_type="test.happened")
        assert event.event_type == "test.happened"


class TestAggregateRoot:
    def test_add_and_collect_events(self) -> None:
        agg = AggregateRoot()
        event = DomainEvent(event_type="test")
        agg.add_event(event)
        assert len(agg.pending_events) == 1
        collected = agg.collect_events()
        assert len(collected) == 1
        assert len(agg.pending_events) == 0

    def test_collect_clears(self) -> None:
        agg = AggregateRoot()
        agg.add_event(DomainEvent(event_type="a"))
        agg.add_event(DomainEvent(event_type="b"))
        events = agg.collect_events()
        assert len(events) == 2
        assert len(agg.collect_events()) == 0
