"""JWT authentication handler."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

import bcrypt
from jose import jwt, JWTError

from orchestrator.config import AuthSettings


class JWTHandler:
    """Handles JWT token creation and validation."""

    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings

    def create_access_token(
        self, subject: str, role: str, tenant_id: str, extra: dict[str, Any] | None = None
    ) -> str:
        """Create a JWT access token."""
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.access_token_expire_minutes
        )
        payload = {
            "sub": subject,
            "role": role,
            "tenant_id": tenant_id,
            "exp": expire,
            "type": "access",
        }
        if extra:
            payload.update(extra)
        encoded: str = cast(
            str,
            jwt.encode(
                payload, self._settings.secret_key, algorithm=self._settings.algorithm
            ),
        )
        return encoded

    def create_refresh_token(self, subject: str) -> str:
        """Create a JWT refresh token."""
        expire = datetime.now(timezone.utc) + timedelta(
            days=self._settings.refresh_token_expire_days
        )
        payload = {
            "sub": subject,
            "exp": expire,
            "type": "refresh",
        }
        encoded: str = cast(
            str,
            jwt.encode(
                payload, self._settings.secret_key, algorithm=self._settings.algorithm
            ),
        )
        return encoded

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token, self._settings.secret_key, algorithms=[self._settings.algorithm]
            )
        except JWTError as e:
            raise InvalidTokenError(f"Invalid token: {e}") from e
        else:
            return cast(dict[str, Any], payload)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt directly."""
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid."""
