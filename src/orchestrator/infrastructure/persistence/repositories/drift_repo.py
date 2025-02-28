"""Drift report repository implementation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator.domain.models.drift import DriftItem, DriftReport
from orchestrator.domain.ports.repositories import DriftReportRepository
from orchestrator.infrastructure.persistence.models import DriftReportORM


class PostgresDriftReportRepository(DriftReportRepository):
    """PostgreSQL implementation of DriftReportRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: DriftReport) -> DriftReport:
        orm = self._to_orm(report)
        self._session.add(orm)
        await self._session.flush()
        return report

    async def get_by_id(self, report_id: str) -> DriftReport | None:
        result = await self._session.execute(
            select(DriftReportORM).where(DriftReportORM.id == report_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_deployment(
        self, deployment_id: str, limit: int = 20
    ) -> list[DriftReport]:
        result = await self._session.execute(
            select(DriftReportORM)
            .where(DriftReportORM.deployment_id == deployment_id)
            .order_by(DriftReportORM.created_at.desc())
            .limit(limit)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_latest_for_deployment(self, deployment_id: str) -> DriftReport | None:
        result = await self._session.execute(
            select(DriftReportORM)
            .where(DriftReportORM.deployment_id == deployment_id)
            .order_by(DriftReportORM.created_at.desc())
            .limit(1)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    def _to_orm(self, report: DriftReport) -> DriftReportORM:
        return DriftReportORM(
            id=report.id,
            deployment_id=report.deployment_id,
            scan_type=report.scan_type,
            items_data=[item.model_dump() for item in report.items],
            summary=report.summary,
            auto_remediate=report.auto_remediate,
            remediation_deployment_id=report.remediation_deployment_id,
            version=report.version,
        )

    def _to_domain(self, orm: DriftReportORM) -> DriftReport:
        items = []
        if orm.items_data:
            items = [DriftItem.model_validate(item) for item in orm.items_data]
        return DriftReport(
            id=orm.id,
            deployment_id=orm.deployment_id,
            scan_type=orm.scan_type,
            items=items,
            summary=orm.summary or "",
            auto_remediate=orm.auto_remediate,
            remediation_deployment_id=orm.remediation_deployment_id,
            version=orm.version,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
