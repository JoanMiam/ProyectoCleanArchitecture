"""Integration tests for the auth router (INS-14).

We boot the FastAPI app against an in-memory SQLite database (via
``aiosqlite``) and override the dependency that yields a DB session so all
routes hit the test schema. Login is exercised end-to-end: a seeded user, a
real bcrypt hash, the real JWT provider, and a real Bearer-token round-trip
against a protected endpoint.

No Docker, no Postgres — same setup the persistence integration tests already
use in this repo.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.infrastructure.auth.password_hasher import BcryptPasswordHasher
from src.infrastructure.persistence.sqlalchemy.models import Base, UserModel
from src.infrastructure.persistence.sqlalchemy.session import (
    make_engine,
    make_session_factory,
)
from src.interfaces.http.deps import get_db_session
from src.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

USER_EMAIL = "alice@example.com"
USER_PASSWORD = "hunter2"


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = make_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return make_session_factory(engine)


@pytest_asyncio.fixture
async def seed_user(session_factory: async_sessionmaker[AsyncSession]) -> UserModel:
    """Insert a user with a real bcrypt hash and return the model."""
    hasher = BcryptPasswordHasher(rounds=4)  # cheap rounds for tests
    now = datetime.now(UTC)
    user = UserModel(
        id=uuid4(),
        email=USER_EMAIL,
        password_hash=hasher.hash(USER_PASSWORD),
        role="inspector",
        created_at=now,
        updated_at=now,
    )
    async with session_factory() as session:
        session.add(user)
        await session.commit()
    return user


@pytest.fixture
def client(session_factory: async_sessionmaker[AsyncSession]) -> Iterator[TestClient]:
    """Boot the app with the DB session dep pointing at the test engine."""

    async def _override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# ----------------------------------------------------------------------
# POST /auth/login
# ----------------------------------------------------------------------


class TestLoginEndpoint:
    def test_login_with_valid_credentials_returns_token(
        self, client: TestClient, seed_user: UserModel
    ) -> None:
        response = client.post(
            "/auth/login",
            json={"email": USER_EMAIL, "password": USER_PASSWORD},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str) and body["access_token"].count(".") == 2

    def test_login_with_wrong_password_returns_401(
        self, client: TestClient, seed_user: UserModel
    ) -> None:
        response = client.post(
            "/auth/login",
            json={"email": USER_EMAIL, "password": "WRONG"},
        )
        assert response.status_code == 401

    def test_login_with_unknown_email_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "whatever"},
        )
        assert response.status_code == 401

    def test_login_with_invalid_payload_returns_422(self, client: TestClient) -> None:
        response = client.post("/auth/login", json={"email": "not-an-email"})
        assert response.status_code == 422


# ----------------------------------------------------------------------
# GET /auth/me (protected endpoint)
# ----------------------------------------------------------------------


class TestProtectedEndpoint:
    def test_returns_user_id_with_valid_token(
        self, client: TestClient, seed_user: UserModel
    ) -> None:
        token = client.post(
            "/auth/login",
            json={"email": USER_EMAIL, "password": USER_PASSWORD},
        ).json()["access_token"]

        response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == str(seed_user.id)
        assert body["role"] == "inspector"

    def test_rejects_request_without_token(self, client: TestClient) -> None:
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_rejects_request_with_invalid_token(self, client: TestClient) -> None:
        response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
        assert response.status_code == 401

    def test_rejects_request_with_wrong_scheme(self, client: TestClient) -> None:
        response = client.get("/auth/me", headers={"Authorization": "Basic abc"})
        assert response.status_code == 401