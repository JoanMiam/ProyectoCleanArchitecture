"""SQLAlchemy-backed :class:`UnitOfWork`.

Each ``async with uow:`` block opens a fresh AsyncSession (from a session
factory) and wraps it in a transactional scope. ``commit()`` and ``rollback()``
delegate to the session; the context manager guarantees the session is closed
and that uncommitted work is rolled back on exception.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.ports.unit_of_work import UnitOfWork
from src.infrastructure.persistence.sqlalchemy.changeset_repository import (
    SQLAlchemyChangeSetRepository,
)
from src.infrastructure.persistence.sqlalchemy.repositories import SQLAlchemyInspectionRepository


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.inspections = SQLAlchemyInspectionRepository(self._session)
        self.changesets = SQLAlchemyChangeSetRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if self._session is None:
                return
            if exc_type is not None:
                await self._session.rollback()
        finally:
            if self._session is not None:
                await self._session.close()
            self._session = None

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active — use `async with uow:` first.")
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active — use `async with uow:` first.")
        await self._session.rollback()
