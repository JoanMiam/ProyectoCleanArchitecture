"""Shared fixtures for persistence integration tests.

The integration tests run against in-memory SQLite (via ``aiosqlite``) so they
do not require Docker, Postgres or any external service. The same models and
mappers work against PostgreSQL in production because we use SQLAlchemy
dialect-neutral types (``Uuid``, ``DateTime(timezone=True)``, ``JSON`` variant).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.infrastructure.persistence.sqlalchemy.models import Base, UserModel
from src.infrastructure.persistence.sqlalchemy.session import make_engine, make_session_factory

# In-memory shared SQLite DB lives for one test only.
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Build an isolated engine, create the schema, dispose at teardown."""
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
async def seed_user(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    """Insert a user so inspections.created_by FK passes; return its id."""
    user_id = uuid4()
    now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    async with session_factory() as session:
        session.add(
            UserModel(
                id=user_id,
                email=f"u-{user_id}@test.local",
                password_hash="x",
                role="inspector",
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()
    return user_id