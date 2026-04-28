"""Fakes for all ports — fast, in-memory, no IO."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from src.application.ports.auth_context import AuthContext
from src.application.ports.clock import Clock
from src.application.ports.inspection_repository import InspectionFilters, InspectionRepository
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.entities.inspection import Inspection
from src.domain.exceptions import InspectionNotFound
from src.domain.value_objects.ids import InspectionId


# ------------------------------------------------------------------
# Fakes
# ------------------------------------------------------------------

class FakeClock(Clock):
    def __init__(self, fixed: datetime | None = None) -> None:
        self._now = fixed or datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: int) -> None:
        from datetime import timedelta
        self._now = self._now + timedelta(seconds=seconds)


class FakeInspectionRepo(InspectionRepository):
    def __init__(self) -> None:
        self._store: dict[InspectionId, Inspection] = {}
        self.saved: list[Inspection] = []

    async def get(self, id: InspectionId) -> Inspection:
        if id not in self._store:
            raise InspectionNotFound(f"Inspection '{id}' not found.")
        return self._store[id]

    async def save(self, inspection: Inspection) -> None:
        self._store[inspection.id] = inspection
        self.saved.append(inspection)

    async def list(self, filters: InspectionFilters | None = None) -> list[Inspection]:
        items = list(self._store.values())
        if filters:
            if filters.status is not None:
                items = [i for i in items if i.status == filters.status]
            if filters.created_by is not None:
                items = [i for i in items if i.created_by == filters.created_by]
        return items[filters.offset : filters.offset + filters.limit] if filters else items

    async def exists(self, id: InspectionId) -> bool:
        return id in self._store


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.inspections: FakeInspectionRepo = FakeInspectionRepo()
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> Self:
        self.committed = False
        self.rolled_back = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


class FakeAuthContext(AuthContext):
    def __init__(self, user_id: UUID, roles: list[str] | None = None) -> None:
        self._user_id = user_id
        self._roles = roles or ["inspector"]

    def current_user_id(self) -> UUID:
        return self._user_id

    def has_role(self, role: str) -> bool:
        return role in self._roles


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def fixed_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def fake_uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def user_id() -> UUID:
    return UUID("00000000-0000-0000-0000-000000000001")
