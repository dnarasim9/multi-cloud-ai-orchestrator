"""Unit tests for event publisher."""

from __future__ import annotations

import pytest

from orchestrator.infrastructure.messaging.event_publisher import InMemoryEventPublisher


class TestInMemoryEventPublisher:
    @pytest.mark.asyncio
    async def test_publish(self) -> None:
        publisher = InMemoryEventPublisher()
        await publisher.publish("test.event", {"key": "value"})
        assert len(publisher.published_events) == 1
        assert publisher.published_events[0] == ("test.event", {"key": "value"})

    @pytest.mark.asyncio
    async def test_publish_batch(self) -> None:
        publisher = InMemoryEventPublisher()
        events = [
            ("event.1", {"id": 1}),
            ("event.2", {"id": 2}),
        ]
        await publisher.publish_batch(events)
        assert len(publisher.published_events) == 2

    @pytest.mark.asyncio
    async def test_subscribe_and_receive(self) -> None:
        publisher = InMemoryEventPublisher()
        received: list = []

        async def handler(payload: dict) -> None:
            received.append(payload)

        publisher.subscribe("test.event", handler)
        await publisher.publish("test.event", {"data": "hello"})
        assert len(received) == 1
        assert received[0]["data"] == "hello"

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        publisher = InMemoryEventPublisher()
        await publisher.publish("test", {})
        publisher.clear()
        assert len(publisher.published_events) == 0
