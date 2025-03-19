"""Authentication API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from orchestrator.api.dependencies.auth import get_current_user, get_jwt_handler
from orchestrator.api.schemas.auth_schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from orchestrator.config import get_settings
from orchestrator.domain.models.user import User
from orchestrator.infrastructure.auth.jwt_handler import JWTHandler
from orchestrator.infrastructure.persistence.repositories.in_memory import (
    InMemoryUserRepository,
)


router = APIRouter(prefix="/auth", tags=["auth"])

# Use the shared module-level user store via the repository.
_user_repo = InMemoryUserRepository()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
) -> UserResponse:
    """Register a new user."""
    existing = await _user_repo.get_by_username(request.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=JWTHandler.hash_password(request.password),
        role=request.role,
        tenant_id=request.tenant_id,
    )
    await _user_repo.save(user)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    jwt_handler: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> TokenResponse:
    """Authenticate and return JWT tokens."""
    user = await _user_repo.get_by_username(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not JWTHandler.verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    settings = get_settings()
    access_token = jwt_handler.create_access_token(
        subject=user.id,
        role=user.role.value,
        tenant_id=user.tenant_id,
    )
    refresh_token = jwt_handler.create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.auth.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Get current user info."""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
    )
