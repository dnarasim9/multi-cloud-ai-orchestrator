"""Unit tests for in-memory repository implementations."""

from __future__ import annotations

import pytest

from orchestrator.domain.models.cloud_provider import CloudProviderType
from orchestrator.domain.models.deployment import (
    Deployment,
    DeploymentIntent,
    DeploymentStatus,
)
from orchestrator.domain.models.drift import DriftReport
from orchestrator.domain.models.task import Task, TaskStatus
from orchestrator.domain.models.user import Role, User
from orchestrator.infrastructure.persistence.repositories.in_memory import (
    InMemoryDeploymentRepository,
    InMemoryDriftReportRepository,
    InMemoryTaskRepository,
    InMemoryUserRepository,
)


def _make_intent() -> DeploymentIntent:
    return DeploymentIntent(
        description="test",
        target_providers=[CloudProviderType.AWS],
    )


def _make_deployment(
    tenant_id: str = "t1", status: DeploymentStatus = DeploymentStatus.PENDING,
) -> Deployment:
    d = Deployment(
        name="test",
        intent=_make_intent(),
        initiated_by="user",
        tenant_id=tenant_id,
    )
    if status != DeploymentStatus.PENDING:
        object.__setattr__(d, "status", status)
    return d


class TestInMemoryDeploymentRepository:
    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        repo = InMemoryDeploymentRepository()
        d = _make_deployment()
        await repo.save(d)
        result = await repo.get_by_id(d.id)
        assert result is not None
        assert result.id == d.id

    @pytest.mark.asyncio
    async def test_get_nonexistent(self) -> None:
        repo = InMemoryDeploymentRepository()
        assert await repo.get_by_id("nope") is None

    @pytest.mark.asyncio
    async def test_list_by_status(self) -> None:
        repo = InMemoryDeploymentRepository()
        d1 = _make_deployment()
        d2 = _make_deployment()
        d2.start_planning()
        await repo.save(d1)
        await repo.save(d2)
        pending = await repo.list_by_status(DeploymentStatus.PENDING)
        assert len(pending) == 1
        planning = await repo.list_by_status(DeploymentStatus.PLANNING)
        assert len(planning) == 1

    @pytest.mark.asyncio
    async def test_list_by_tenant(self) -> None:
        repo = InMemoryDeploymentRepository()
        await repo.save(_make_deployment(tenant_id="a"))
        await repo.save(_make_deployment(tenant_id="a"))
        await repo.save(_make_deployment(tenant_id="b"))
        assert len(await repo.list_by_tenant("a")) == 2
        assert len(await repo.list_by_tenant("b")) == 1

    @pytest.mark.asyncio
    async def test_update(self) -> None:
        repo = InMemoryDeploymentRepository()
        d = _make_deployment()
        await repo.save(d)
        d.start_planning()
        await repo.update(d)
        result = await repo.get_by_id(d.id)
        assert result.status == DeploymentStatus.PLANNING

    @pytest.mark.asyncio
    async def test_count_by_status(self) -> None:
        repo = InMemoryDeploymentRepository()
        await repo.save(_make_deployment())
        await repo.save(_make_deployment())
        assert await repo.count_by_status(DeploymentStatus.PENDING) == 2
        assert await repo.count_by_status(DeploymentStatus.COMPLETED) == 0

    @pytest.mark.asyncio
    async def test_list_with_limit_offset(self) -> None:
        repo = InMemoryDeploymentRepository()
        for _ in range(5):
            await repo.save(_make_deployment())
        result = await repo.list_by_status(DeploymentStatus.PENDING, limit=2, offset=1)
        assert len(result) == 2


def _make_task(
    deployment_id: str = "d1",
    step_id: str = "s1",
    name: str = "t1",
) -> Task:
    return Task(
        deployment_id=deployment_id,
        step_id=step_id,
        name=name,
        provider=CloudProviderType.AWS,
        terraform_action="create",
    )


class TestInMemoryTaskRepository:
    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        repo = InMemoryTaskRepository()
        t = _make_task(name="task1")
        await repo.save(t)
        assert await repo.get_by_id(t.id) is not None

    @pytest.mark.asyncio
    async def test_get_nonexistent(self) -> None:
        repo = InMemoryTaskRepository()
        assert await repo.get_by_id("nope") is None

    @pytest.mark.asyncio
    async def test_list_by_deployment(self) -> None:
        repo = InMemoryTaskRepository()
        t1 = _make_task(deployment_id="d1", step_id="s1", name="t1")
        t2 = _make_task(deployment_id="d1", step_id="s2", name="t2")
        t3 = _make_task(deployment_id="d2", step_id="s3", name="t3")
        await repo.save(t1)
        await repo.save(t2)
        await repo.save(t3)
        assert len(await repo.list_by_deployment("d1")) == 2
        assert len(await repo.list_by_deployment("d2")) == 1

    @pytest.mark.asyncio
    async def test_list_by_status(self) -> None:
        repo = InMemoryTaskRepository()
        t = _make_task()
        t.enqueue()
        await repo.save(t)
        assert len(await repo.list_by_status(TaskStatus.QUEUED)) == 1
        assert len(await repo.list_by_status(TaskStatus.PENDING)) == 0

    @pytest.mark.asyncio
    async def test_acquire_next(self) -> None:
        repo = InMemoryTaskRepository()
        t = _make_task()
        t.enqueue()
        await repo.save(t)
        acquired = await repo.acquire_next("w1")
        assert acquired is not None
        assert acquired.worker_id == "w1"
        assert acquired.status == TaskStatus.ACQUIRED

    @pytest.mark.asyncio
    async def test_acquire_next_empty(self) -> None:
        repo = InMemoryTaskRepository()
        assert await repo.acquire_next("w1") is None

    @pytest.mark.asyncio
    async def test_list_by_worker(self) -> None:
        repo = InMemoryTaskRepository()
        t = _make_task()
        t.enqueue()
        await repo.save(t)
        await repo.acquire_next("w1")
        assert len(await repo.list_by_worker("w1")) == 1
        assert len(await repo.list_by_worker("w2")) == 0

    @pytest.mark.asyncio
    async def test_update(self) -> None:
        repo = InMemoryTaskRepository()
        t = _make_task()
        await repo.save(t)
        t.enqueue()
        await repo.update(t)
        result = await repo.get_by_id(t.id)
        assert result.status == TaskStatus.QUEUED


class TestInMemoryDriftReportRepository:
    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        repo = InMemoryDriftReportRepository()
        report = DriftReport(deployment_id="d1")
        await repo.save(report)
        assert await repo.get_by_id(report.id) is not None

    @pytest.mark.asyncio
    async def test_get_nonexistent(self) -> None:
        repo = InMemoryDriftReportRepository()
        assert await repo.get_by_id("nope") is None

    @pytest.mark.asyncio
    async def test_list_by_deployment(self) -> None:
        repo = InMemoryDriftReportRepository()
        await repo.save(DriftReport(deployment_id="d1"))
        await repo.save(DriftReport(deployment_id="d1"))
        await repo.save(DriftReport(deployment_id="d2"))
        assert len(await repo.list_by_deployment("d1")) == 2

    @pytest.mark.asyncio
    async def test_get_latest(self) -> None:
        repo = InMemoryDriftReportRepository()
        r1 = DriftReport(deployment_id="d1", summary="first")
        r2 = DriftReport(deployment_id="d1", summary="second")
        await repo.save(r1)
        await repo.save(r2)
        latest = await repo.get_latest_for_deployment("d1")
        assert latest is not None

    @pytest.mark.asyncio
    async def test_get_latest_empty(self) -> None:
        repo = InMemoryDriftReportRepository()
        assert await repo.get_latest_for_deployment("d1") is None


class TestInMemoryUserRepository:
    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        repo = InMemoryUserRepository()
        user = User(username="test", email="test@t.com", role=Role.VIEWER)
        await repo.save(user)
        assert await repo.get_by_id(user.id) is not None

    @pytest.mark.asyncio
    async def test_get_by_username(self) -> None:
        repo = InMemoryUserRepository()
        user = User(username="alice", email="a@t.com", role=Role.ADMIN)
        await repo.save(user)
        result = await repo.get_by_username("alice")
        assert result is not None
        assert result.email == "a@t.com"

    @pytest.mark.asyncio
    async def test_get_by_username_not_found(self) -> None:
        repo = InMemoryUserRepository()
        assert await repo.get_by_username("nobody") is None

    @pytest.mark.asyncio
    async def test_list_by_tenant(self) -> None:
        repo = InMemoryUserRepository()
        await repo.save(User(username="a", email="a@t.com", tenant_id="t1"))
        await repo.save(User(username="b", email="b@t.com", tenant_id="t1"))
        await repo.save(User(username="c", email="c@t.com", tenant_id="t2"))
        assert len(await repo.list_by_tenant("t1")) == 2

    @pytest.mark.asyncio
    async def test_update(self) -> None:
        repo = InMemoryUserRepository()
        user = User(username="test", email="old@t.com", role=Role.VIEWER)
        await repo.save(user)
        user.email = "new@t.com"
        await repo.update(user)
        result = await repo.get_by_id(user.id)
        assert result.email == "new@t.com"
