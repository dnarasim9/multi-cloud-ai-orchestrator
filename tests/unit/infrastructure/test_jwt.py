"""Unit tests for JWT handler."""

from __future__ import annotations

import pytest

from orchestrator.config import AuthSettings
from orchestrator.infrastructure.auth.jwt_handler import InvalidTokenError, JWTHandler


@pytest.fixture
def handler() -> JWTHandler:
    return JWTHandler(AuthSettings(
        secret_key="test-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
    ))


class TestJWTHandler:
    def test_create_and_decode_access_token(self, handler: JWTHandler) -> None:
        token = handler.create_access_token(
            subject="user-123",
            role="admin",
            tenant_id="tenant-1",
        )
        payload = handler.decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"
        assert payload["tenant_id"] == "tenant-1"
        assert payload["type"] == "access"

    def test_create_refresh_token(self, handler: JWTHandler) -> None:
        token = handler.create_refresh_token(subject="user-123")
        payload = handler.decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    def test_invalid_token_raises(self, handler: JWTHandler) -> None:
        with pytest.raises(InvalidTokenError):
            handler.decode_token("invalid.token.here")

    def test_password_hashing(self) -> None:
        password = "test_password_123"
        hashed = JWTHandler.hash_password(password)
        assert JWTHandler.verify_password(password, hashed)
        assert not JWTHandler.verify_password("wrong_password", hashed)

    def test_extra_claims(self, handler: JWTHandler) -> None:
        token = handler.create_access_token(
            subject="user-123",
            role="admin",
            tenant_id="t-1",
            extra={"custom_field": "custom_value"},
        )
        payload = handler.decode_token(token)
        assert payload["custom_field"] == "custom_value"
