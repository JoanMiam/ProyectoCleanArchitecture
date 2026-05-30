"""Integration tests for SQLAlchemyAuditRepository against in-memory SQLite."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.entities.inspection import Inspection
from src.domain.events import InspectionCreated, ObservationAdded
from src.domain.value_objects.ids import InspectionId, UserId
from src.infrastructure.persistence.sqlalchemy.audit_repository import SQLAlchemyAuditRepository


@pytest_asyncio.fixture
async def audit_repo(
    session_factory: async_sessionmaker[AsyncSession],
) -> SQLAlchemyAuditRepository:
    session = session_factory()
    return SQLAlchemyAuditRepository(session)


@pytest.mark.asyncio
@pytest.mark.integration
class TestSQLAlchemyAuditRepository:
    async def test_append_and_list_returns_entry(
        self,
        audit_repo: SQLAlchemyAuditRepository,
    ) -> None:
        inspection_id = InspectionId(uuid4())
        user_id = UserId(uuid4())
        now = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)

        event = InspectionCreated(
            occurred_at=now,
            inspection_id=inspection_id,
            created_by=user_id,
        )
        await audit_repo.append(event)
        await audit_repo._session.commit()

        entries = await audit_repo.list_for_inspection(inspection_id)

        assert len(entries) == 1
        entry = entries[0]
        assert entry.event_type == "InspectionCreated"
        assert entry.aggregate_id == inspection_id
        assert entry.actor_id == user_id
        assert entry.aggregate_type == "Inspection"

    async def test_append_many_persists_all(
        self,
        audit_repo: SQLAlchemyAuditRepository,
    ) -> None:
        inspection_id = InspectionId(uuid4())
        user_id = UserId(uuid4())
        obs_id = uuid4()
        now = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)

        events = [
            InspectionCreated(occurred_at=now, inspection_id=inspection_id, created_by=user_id),
            ObservationAdded(
                occurred_at=now,
                inspection_id=inspection_id,
                observation_id=obs_id,
                added_by=user_id,
            ),
        ]
        await audit_repo.append_many(events)
        await audit_repo._session.commit()

        entries = await audit_repo.list_for_inspection(inspection_id)

        assert len(entries) == 2
        types = {e.event_type for e in entries}
        assert types == {"InspectionCreated", "ObservationAdded"}

    async def test_filters_by_inspection_id(
        self,
        audit_repo: SQLAlchemyAuditRepository,
    ) -> None:
        id_a = InspectionId(uuid4())
        id_b = InspectionId(uuid4())
        user_id = UserId(uuid4())
        now = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)

        await audit_repo.append(
            InspectionCreated(occurred_at=now, inspection_id=id_a, created_by=user_id)
        )
        await audit_repo.append(
            InspectionCreated(occurred_at=now, inspection_id=id_b, created_by=user_id)
        )
        await audit_repo._session.commit()

        entries_a = await audit_repo.list_for_inspection(id_a)
        assert len(entries_a) == 1
        assert entries_a[0].aggregate_id == id_a

    async def test_empty_returns_empty_list(
        self,
        audit_repo: SQLAlchemyAuditRepository,
    ) -> None:
        entries = await audit_repo.list_for_inspection(InspectionId(uuid4()))
        assert entries == []

    async def test_collect_events_from_inspection_aggregate(
        self,
        audit_repo: SQLAlchemyAuditRepository,
    ) -> None:
        user_id = UserId(uuid4())
        now = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
        inspection = Inspection.create(
            id=InspectionId(uuid4()),
            title="Safety check",
            location="Floor B",
            created_by=user_id,
            now=now,
        )
        events = inspection.collect_events()
        await audit_repo.append_many(events)
        await audit_repo._session.commit()

        entries = await audit_repo.list_for_inspection(inspection.id)
        assert len(entries) == 1
        assert entries[0].event_type == "InspectionCreated"
        assert entries[0].actor_id == user_id
