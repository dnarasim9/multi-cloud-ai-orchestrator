"""Unit tests for application configuration."""

from __future__ import annotations

import pytest

from orchestrator.config import (
    AuthSettings,
    DatabaseSettings,
    Environment,
    KafkaSettings,
    ObservabilitySettings,
    RateLimitSettings,
    RedisSettings,
    Settings,
)


class TestDatabaseSettings:
    def test_defaults(self) -> None:
        settings = DatabaseSettings()
        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.pool_size == 20

    def test_async_url(self) -> None:
        settings = DatabaseSettings(host="db", port=5432, name="test", user="u", password="p")
        assert settings.async_url == "postgresql+asyncpg://u:p@db:5432/test"

    def test_sync_url(self) -> None:
        settings = DatabaseSettings(host="db", port=5432, name="test", user="u", password="p")
        assert settings.sync_url == "postgresql://u:p@db:5432/test"


class TestRedisSettings:
    def test_defaults(self) -> None:
        settings = RedisSettings()
        assert settings.host == "localhost"
        assert settings.port == 6379

    def test_url_without_password(self) -> None:
        settings = RedisSettings(host="redis", port=6379, password="", db=0)
        assert settings.url == "redis://redis:6379/0"

    def test_url_with_password(self) -> None:
        settings = RedisSettings(host="redis", port=6379, password="secret", db=1)
        assert settings.url == "redis://:secret@redis:6379/1"


class TestKafkaSettings:
    def test_defaults(self) -> None:
        settings = KafkaSettings()
        assert settings.enabled is False
        assert settings.topic_prefix == "orchestrator"


class TestAuthSettings:
    def test_defaults(self) -> None:
        settings = AuthSettings()
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 30


class TestObservabilitySettings:
    def test_defaults(self) -> None:
        settings = ObservabilitySettings()
        assert settings.log_level == "INFO"
        assert settings.metrics_enabled is True
        assert settings.tracing_enabled is True


class TestRateLimitSettings:
    def test_defaults(self) -> None:
        settings = RateLimitSettings()
        assert settings.requests_per_minute == 60
        assert settings.burst_size == 10


class TestSettings:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        settings = Settings()
        assert settings.environment == Environment.DEVELOPMENT
        assert settings.debug is False
        assert settings.api_prefix == "/api/v1"

    def test_nested_settings(self) -> None:
        settings = Settings()
        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.redis, RedisSettings)
        assert isinstance(settings.auth, AuthSettings)


class TestEnvironment:
    def test_values(self) -> None:
        assert Environment.DEVELOPMENT == "development"
        assert Environment.PRODUCTION == "production"
        assert Environment.TESTING == "testing"
        assert Environment.STAGING == "staging"
