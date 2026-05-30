"""Unit tests for :class:`JwtTokenProvider`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from src.application.ports.token_provider import InvalidTokenError
from src.domain.value_objects.ids import UserId
from src.infrastructure.auth.jwt_provider import JwtTokenProvider

NOW = datetime.now(UTC) + timedelta(days=1)  # ahead of wall-clock so decode sees it valid
USER_ID = UserId(UUID("00000000-0000-0000-0000-0000000000a1"))


def _provider(secret: str = "test-secret", ttl: int = 60) -> JwtTokenProvider:
    return JwtTokenProvider(secret=secret, ttl_minutes=ttl)


class TestIssue:
    def test_round_trip_returns_user_id_and_role(self) -> None:
        provider = _provider()
        token = provider.issue(USER_ID, "inspector", NOW)
        claims = provider.decode(token)
        assert claims.user_id == USER_ID
        assert claims.role == "inspector"

    def test_token_expires_after_configured_ttl(self) -> None:
        provider = _provider(ttl=30)
        token = provider.issue(USER_ID, "inspector", NOW)
        claims = provider.decode(token)
        assert claims.expires_at - claims.issued_at == timedelta(minutes=30)


class TestDecodeFailure:
    def test_rejects_token_signed_with_different_secret(self) -> None:
        token = _provider("secret-a").issue(USER_ID, "inspector", NOW)
        with pytest.raises(InvalidTokenError):
            _provider("secret-b").decode(token)

    def test_rejects_garbage_string(self) -> None:
        with pytest.raises(InvalidTokenError):
            _provider().decode("not-a-token")

    def test_rejects_expired_token(self) -> None:
        provider = _provider(ttl=1)
        past = datetime.now(UTC) - timedelta(hours=1)
        token = provider.issue(USER_ID, "inspector", past)
        with pytest.raises(InvalidTokenError):
            provider.decode(token)


class TestConstruction:
    def test_empty_secret_rejected(self) -> None:
        with pytest.raises(ValueError):
            JwtTokenProvider(secret="")