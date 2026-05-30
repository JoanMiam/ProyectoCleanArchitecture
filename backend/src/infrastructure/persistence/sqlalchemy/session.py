"""Async SQLAlchemy engine and session factory.

The engine is created lazily on first access so importing this module does not
require a reachable database (important for unit tests and `--collect-only`).
Use :func:`make_engine` and :func:`make_session_factory` to build isolated
engines (e.g. SQLite in-memory) in integration tests.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def make_engine(url: str, *, echo: bool = False) -> AsyncEngine:
    """Build an isolated async engine. Used by tests and by the default factory."""
    return create_async_engine(url, echo=echo, future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build a session factory bound to ``engine``.

    ``expire_on_commit=False`` keeps ORM objects usable after ``commit()`` so the
    UnitOfWork can return mapped data without forcing a reload.
    """
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def get_engine() -> AsyncEngine:
    """Process-wide engine bound to ``settings.database_url`` (lazy)."""
    global _engine
    if _engine is None:
        _engine = make_engine(get_settings().database_url)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Process-wide session factory bound to the default engine (lazy)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = make_session_factory(get_engine())
    return _session_factory


async def dispose_engine() -> None:
    """Close the default engine. Call on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None