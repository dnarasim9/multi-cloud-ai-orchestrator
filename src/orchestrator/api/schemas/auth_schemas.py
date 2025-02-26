"""API schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from orchestrator.domain.models.user import Role


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    password: str = Field(..., min_length=8)
    role: Role = Role.VIEWER
    tenant_id: str = "default"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: Role
    tenant_id: str
    is_active: bool
