"""Redis cache and distributed lock implementations."""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis.asyncio
import structlog

from orchestrator.config import RedisSettings
from orchestrator.domain.ports.services import CacheService, DistributedLock


logger = structlog.get_logger(__name__)


class RedisCacheService(CacheService):
    """Redis implementation of CacheService."""

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def get(self, key: str) -> Any | None:
        value = await self._client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value.decode("utf-8") if isinstance(value, bytes) else value

    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await self._client.setex(key, ttl_seconds, serialized)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(key))


class RedisDistributedLock(DistributedLock):
    """Redis implementation of distributed locking using SETNX."""

    def __init__(self, client: redis.Redis) -> None:
        self._client = client
        self._lock_values: dict[str, str] = {}

    async def acquire(self, resource_id: str, ttl_seconds: int = 30) -> bool:
        lock_key = f"lock:{resource_id}"
        lock_value = str(uuid.uuid4())

        acquired = await self._client.set(
            lock_key, lock_value, nx=True, ex=ttl_seconds
        )
        if acquired:
            self._lock_values[resource_id] = lock_value
            logger.debug("lock_acquired", resource_id=resource_id, ttl=ttl_seconds)
            return True

        logger.debug("lock_not_acquired", resource_id=resource_id)
        return False

    async def release(self, resource_id: str) -> bool:
        lock_key = f"lock:{resource_id}"
        lock_value = self._lock_values.get(resource_id)
        if lock_value is None:
            return False

        # Atomic check-and-delete using Lua script
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self._client.eval(script, 1, lock_key, lock_value)
        if result:
            del self._lock_values[resource_id]
            logger.debug("lock_released", resource_id=resource_id)
            return True
        return False

    async def extend(self, resource_id: str, ttl_seconds: int = 30) -> bool:
        lock_key = f"lock:{resource_id}"
        lock_value = self._lock_values.get(resource_id)
        if lock_value is None:
            return False

        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        result = await self._client.eval(
            script, 1, lock_key, lock_value, str(ttl_seconds)
        )
        return bool(result)

    async def is_locked(self, resource_id: str) -> bool:
        lock_key = f"lock:{resource_id}"
        return bool(await self._client.exists(lock_key))


def create_redis_client(settings: RedisSettings) -> redis.Redis:
    """Factory function to create a Redis client."""
    return redis.Redis.from_url(
        settings.url,
        decode_responses=False,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        retry_on_timeout=True,
    )
