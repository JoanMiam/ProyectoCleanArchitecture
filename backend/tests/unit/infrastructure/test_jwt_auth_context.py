"""Unit tests for :class:`JwtAuthContext`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.application.ports.token_provider import TokenClaims
from src.domain.value_objects.ids import UserId
from src.infrastructure.auth.jwt_auth_context import JwtAuthContext

USER_ID = UserId(UUID("00000000-0000-0000-0000-0000000000a1"))
NOW = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)


def _claims(role: str = "inspector") -> TokenClaims:
    return TokenClaims(
        user_id=USER_ID,
        role=role,
        issued_at=NOW,
        expires_at=NOW + timedelta(hours=1),
    )


class TestJwtAuthContext:
    def test_current_user_id_returns_subject(self) -> None:
        ctx = JwtAuthContext.from_claims(_claims())
        assert ctx.current_user_id() == USER_ID

    def test_has_role_matches_token_role(self) -> None:
        ctx = JwtAuthContext.from_claims(_claims(role="admin"))
        assert ctx.has_role("admin") is True
        assert ctx.has_role("inspector") is False

    def test_has_role_is_exact_match(self) -> None:
        ctx = JwtAuthContext.from_claims(_claims(role="admin"))
        assert ctx.has_role("ADMIN") is False