"""Service dependencies for FastAPI dependency injection."""

from __future__ import annotations

from orchestrator.config import get_settings
from orchestrator.domain.ports.services import (
    CacheService,
    DistributedLock,
    DriftDetector,
    EventPublisher,
    PlanningEngine,
    TerraformExecutor,
)
from orchestrator.infrastructure.ai.drift_detector import SimulatedDriftDetector
from orchestrator.infrastructure.ai.planning_engine import RuleBasedPlanningEngine
from orchestrator.infrastructure.cache.redis_cache import (
    create_redis_client,
    RedisCacheService,
    RedisDistributedLock,
)
from orchestrator.infrastructure.messaging.event_publisher import InMemoryEventPublisher
from orchestrator.infrastructure.terraform.executor import SimulatedTerraformExecutor


class ServiceContainer:
    """Simple dependency injection container.

    Implements the Composition Root pattern for assembling
    dependencies and managing their lifecycle.
    """

    _instance: ServiceContainer | None = None

    def __init__(self) -> None:
        self._settings = get_settings()
        self._event_publisher = InMemoryEventPublisher()
        self._planning_engine = RuleBasedPlanningEngine()
        self._terraform_executor = SimulatedTerraformExecutor()
        self._drift_detector = SimulatedDriftDetector()

        # Redis services (lazy init)
        self._redis_client = None
        self._cache_service: CacheService | None = None
        self._lock_service: DistributedLock | None = None

    @classmethod
    def get_instance(cls) -> ServiceContainer:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    @property
    def event_publisher(self) -> EventPublisher:
        return self._event_publisher

    @property
    def planning_engine(self) -> PlanningEngine:
        return self._planning_engine

    @property
    def terraform_executor(self) -> TerraformExecutor:
        return self._terraform_executor

    @property
    def drift_detector(self) -> DriftDetector:
        return self._drift_detector

    @property
    def lock_service(self) -> DistributedLock:
        if self._lock_service is None:
            client = create_redis_client(self._settings.redis)
            self._lock_service = RedisDistributedLock(client)
        return self._lock_service

    @property
    def cache_service(self) -> CacheService:
        if self._cache_service is None:
            client = create_redis_client(self._settings.redis)
            self._cache_service = RedisCacheService(client)
        return self._cache_service


def get_service_container() -> ServiceContainer:
    return ServiceContainer.get_instance()
