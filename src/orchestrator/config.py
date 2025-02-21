"""Application configuration using pydantic-settings."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    host: str = Field(default="localhost", alias="DB_HOST")
    port: int = Field(default=5432, alias="DB_PORT")
    name: str = Field(default="orchestrator", alias="DB_NAME")
    user: str = Field(default="orchestrator", alias="DB_USER")
    password: str = Field(default="", alias="DB_PASSWORD")
    pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def sync_url(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    model_config = {"env_prefix": "DB_", "extra": "ignore", "populate_by_name": True}


class RedisSettings(BaseSettings):
    """Redis configuration."""

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    password: str = Field(default="", alias="REDIS_PASSWORD")
    db: int = Field(default=0, alias="REDIS_DB")
    lock_timeout: int = Field(default=30, alias="REDIS_LOCK_TIMEOUT")
    lock_retry_interval: float = Field(default=0.1, alias="REDIS_LOCK_RETRY_INTERVAL")

    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"

    model_config = {"env_prefix": "REDIS_", "extra": "ignore", "populate_by_name": True}


class KafkaSettings(BaseSettings):
    """Kafka configuration."""

    bootstrap_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    topic_prefix: str = Field(default="orchestrator", alias="KAFKA_TOPIC_PREFIX")
    consumer_group: str = Field(default="orchestrator-group", alias="KAFKA_CONSUMER_GROUP")
    enabled: bool = Field(default=False, alias="KAFKA_ENABLED")

    model_config = {"env_prefix": "KAFKA_", "extra": "ignore", "populate_by_name": True}


class AuthSettings(BaseSettings):
    """Authentication configuration."""

    secret_key: str = Field(default="change-me-in-production", alias="AUTH_SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="AUTH_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="AUTH_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="AUTH_REFRESH_TOKEN_EXPIRE_DAYS")

    model_config = {"env_prefix": "AUTH_", "extra": "ignore", "populate_by_name": True}


class ObservabilitySettings(BaseSettings):
    """Observability configuration."""

    otlp_endpoint: str = Field(default="http://localhost:4317", alias="OTLP_ENDPOINT")
    service_name: str = Field(default="deployment-orchestrator", alias="SERVICE_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    tracing_enabled: bool = Field(default=True, alias="TRACING_ENABLED")

    model_config = {"env_prefix": "OBS_", "extra": "ignore", "populate_by_name": True}


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration."""

    requests_per_minute: int = Field(default=60, alias="RATE_LIMIT_RPM")
    burst_size: int = Field(default=10, alias="RATE_LIMIT_BURST")

    model_config = {"env_prefix": "RATE_LIMIT_", "extra": "ignore", "populate_by_name": True}


class Settings(BaseSettings):
    """Main application settings."""

    environment: Environment = Field(default=Environment.DEVELOPMENT, alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    host: str = Field(default="0.0.0.0", alias="HOST")  # noqa: S104
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=4, alias="WORKERS")
    graceful_shutdown_timeout: int = Field(default=30, alias="GRACEFUL_SHUTDOWN_TIMEOUT")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)

    model_config = {"env_prefix": "", "extra": "ignore", "populate_by_name": True}


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
