"""Unit tests for the Login use case (INS-14).

Pure-Python tests with in-memory fakes for every port — no DB, no HTTP, no
bcrypt, no JWT. The goal is to pin the application-layer contract: the use
case orchestrates the four ports correctly and propagates failures as
:class:`InvalidCredentialsError`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.application.dto.auth_dto import LoginInput
from src.application.ports.clock import Clock
from src.application.ports.password_hasher import PasswordHasher
from src.application.ports.token_provider import TokenClaims, TokenProvider
from src.application.ports.user_repository import UserRepository
from src.application.use_cases.login import InvalidCredentialsError, Login
from src.domain.entities.user import User
from src.domain.value_objects.ids import UserId

NOW = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
USER_ID = UserId(UUID("00000000-0000-0000-0000-0000000000a1"))


# ----------------------------------------------------------------------
# Fakes
# ----------------------------------------------------------------------


class FakeUserRepository(UserRepository):
    def __init__(self, users: list[User] | None = None) -> None:
        self._by_email = {u.email: u for u in users or []}
        self._by_id = {u.id: u for u in users or []}

    async def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email)

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self._by_id.get(user_id)


class FakePasswordHasher(PasswordHasher):
    """Identity 'hash' — the stored hash IS the plain password (test only)."""

    def hash(self, plain_password: str) -> str:
        return plain_password

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return plain_password == hashed_password


class FakeTokenProvider(TokenProvider):
    def __init__(self) -> None:
        self.issued: list[tuple[UserId, str, datetime]] = []

    def issue(self, user_id: UserId, role: str, now: datetime) -> str:
        self.issued.append((user_id, role, now))
        return f"token-for-{user_id}"

    def decode(self, token: str) -> TokenClaims:  # not exercised here
        raise NotImplementedError


class FixedClock(Clock):
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _user(email: str = "alice@example.com", password_hash: str = "secret") -> User:
    return User(
        id=USER_ID,
        email=email,
        password_hash=password_hash,
        role="inspector",
        created_at=NOW,
        updated_at=NOW,
    )


def _build_login(user: User | None) -> tuple[Login, FakeTokenProvider]:
    users = FakeUserRepository([user] if user is not None else [])
    tokens = FakeTokenProvider()
    use_case = Login(
        users=users,
        hasher=FakePasswordHasher(),
        tokens=tokens,
        clock=FixedClock(NOW),
    )
    return use_case, tokens


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


class TestLoginSuccess:
    async def test_returns_access_token_for_valid_credentials(self) -> None:
        login, _ = _build_login(_user())
        result = await login.execute(LoginInput("alice@example.com", "secret"))
        assert result.access_token == f"token-for-{USER_ID}"
        assert result.token_type == "bearer"

    async def test_issues_token_with_user_id_role_and_clock_now(self) -> None:
        login, tokens = _build_login(_user())
        await login.execute(LoginInput("alice@example.com", "secret"))
        assert tokens.issued == [(USER_ID, "inspector", NOW)]


class TestLoginFailure:
    async def test_unknown_email_raises_invalid_credentials(self) -> None:
        login, _ = _build_login(None)
        with pytest.raises(InvalidCredentialsError):
            await login.execute(LoginInput("nobody@example.com", "secret"))

    async def test_wrong_password_raises_invalid_credentials(self) -> None:
        login, _ = _build_login(_user(password_hash="real-secret"))
        with pytest.raises(InvalidCredentialsError):
            await login.execute(LoginInput("alice@example.com", "wrong"))

    async def test_failure_does_not_issue_token(self) -> None:
        login, tokens = _build_login(_user(password_hash="real-secret"))
        with pytest.raises(InvalidCredentialsError):
            await login.execute(LoginInput("alice@example.com", "wrong"))
        assert tokens.issued == []

    async def test_same_error_for_unknown_email_and_wrong_password(self) -> None:
        """Same exception type to avoid user-enumeration leaks."""
        login_a, _ = _build_login(None)
        login_b, _ = _build_login(_user(password_hash="real-secret"))
        with pytest.raises(InvalidCredentialsError):
            await login_a.execute(LoginInput("nobody@example.com", "x"))
        with pytest.raises(InvalidCredentialsError):
            await login_b.execute(LoginInput("alice@example.com", "x"))