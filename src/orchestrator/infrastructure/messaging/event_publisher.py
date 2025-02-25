"""Event publisher implementations."""

from __future__ import annotations

import json
from typing import Any

import structlog

from orchestrator.domain.ports.services import EventPublisher


logger = structlog.get_logger(__name__)


class InMemoryEventPublisher(EventPublisher):
    """In-memory event publisher for development/testing."""

    def __init__(self) -> None:
        self._events: list[tuple[str, dict[str, Any]]] = []
        self._handlers: dict[str, list[Any]] = {}

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self._events.append((event_type, payload))
        logger.info("event_published", event_type=event_type, payload_keys=list(payload.keys()))

        for handler in self._handlers.get(event_type, []):
            await handler(payload)

    async def publish_batch(self, events: list[tuple[str, dict[str, Any]]]) -> None:
        for event_type, payload in events:
            await self.publish(event_type, payload)

    def subscribe(self, event_type: str, handler: Any) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    @property
    def published_events(self) -> list[tuple[str, dict[str, Any]]]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()


class KafkaEventPublisher(EventPublisher):
    """Kafka implementation of EventPublisher."""

    def __init__(self, producer: Any, topic_prefix: str = "orchestrator") -> None:
        self._producer = producer
        self._topic_prefix = topic_prefix

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        topic = f"{self._topic_prefix}.{event_type}"
        value = json.dumps(payload, default=str).encode("utf-8")

        await self._producer.send_and_wait(topic, value=value)
        logger.info("kafka_event_published", topic=topic)

    async def publish_batch(self, events: list[tuple[str, dict[str, Any]]]) -> None:
        for event_type, payload in events:
            topic = f"{self._topic_prefix}.{event_type}"
            value = json.dumps(payload, default=str).encode("utf-8")
            await self._producer.send(topic, value=value)

        await self._producer.flush()
        logger.info("kafka_batch_published", event_count=len(events))
