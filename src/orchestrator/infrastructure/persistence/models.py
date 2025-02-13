"""SQLAlchemy ORM models."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    func,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class DeploymentORM(Base):
    __tablename__ = "deployments"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, index=True)
    intent_data = Column(JSON, nullable=False)
    plan_data = Column(JSON, nullable=True)
    step_results_data = Column(JSON, nullable=True, default=list)
    initiated_by = Column(String(255), nullable=False)
    tenant_id = Column(String(100), nullable=False, index=True)
    error_message = Column(Text, nullable=True, default="")
    rollback_deployment_id = Column(String(36), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_deployments_tenant_status", "tenant_id", "status"),
        Index("ix_deployments_created_at", "created_at"),
    )


class TaskORM(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True)
    deployment_id = Column(String(36), nullable=False, index=True)
    step_id = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True, default="")
    status = Column(String(50), nullable=False, index=True)
    provider = Column(String(20), nullable=False)
    terraform_action = Column(String(50), nullable=False)
    worker_id = Column(String(100), nullable=True, index=True)
    idempotency_key = Column(String(36), nullable=False, unique=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    max_attempts = Column(Integer, nullable=False, default=3)
    timeout_seconds = Column(Integer, nullable=False, default=300)
    input_data = Column(JSON, nullable=True, default=dict)
    output_data = Column(JSON, nullable=True, default=dict)
    error_message = Column(Text, nullable=True, default="")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_tasks_deployment_status", "deployment_id", "status"),
        Index("ix_tasks_status_created", "status", "created_at"),
    )


class DriftReportORM(Base):
    __tablename__ = "drift_reports"

    id = Column(String(36), primary_key=True)
    deployment_id = Column(String(36), nullable=False, index=True)
    scan_type = Column(String(50), nullable=False, default="scheduled")
    items_data = Column(JSON, nullable=True, default=list)
    summary = Column(Text, nullable=True, default="")
    auto_remediate = Column(Boolean, nullable=False, default=False)
    remediation_deployment_id = Column(String(36), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_drift_reports_deployment_created", "deployment_id", "created_at"),
    )


class UserORM(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="viewer")
    tenant_id = Column(String(100), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
