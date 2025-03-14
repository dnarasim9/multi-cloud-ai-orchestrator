"""Authentication dependencies for FastAPI."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import (
    Depends,
    HTTPException,
    Security,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from orchestrator.config import get_settings
from orchestrator.domain.models.user import Permission, Role, User
from orchestrator.infrastructure.auth.jwt_handler import InvalidTokenError, JWTHandler


security = HTTPBearer()


def get_jwt_handler() -> JWTHandler:
    settings = get_settings()
    return JWTHandler(settings.auth)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security)],
    jwt_handler: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> User:
    """Extract and validate the current user from JWT token."""
    try:
        payload = jwt_handler.decode_token(credentials.credentials)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    return User(
        id=payload["sub"],
        username=payload.get("username", payload["sub"]),
        email=payload.get("email", ""),
        role=Role(payload.get("role", "viewer")),
        tenant_id=payload.get("tenant_id", "default"),
    )


def require_permission(*permissions: Permission) -> Callable[..., Coroutine[Any, Any, User]]:
    """Dependency factory that requires specific permissions."""

    async def check_permissions(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not user.has_any_permission(*permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[p.value for p in permissions]}",
            )
        return user

    return check_permissions
