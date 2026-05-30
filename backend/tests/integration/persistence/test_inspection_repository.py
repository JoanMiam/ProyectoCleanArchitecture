"""Integration tests for the SQLAlchemy adapters (INS-5).

Cover the criteria in the issue:
- Save & retrieve an inspection with observations and evidences.
- Mapper preserves id, status, version, created_by, created_at, updated_at.
- UnitOfWork commit / rollback / context manager.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.entities.inspection import Inspection
from src.domain.exceptions import InspectionNotFoundError
from src.domain.value_objects.ids import EvidenceId, InspectionId, UserId
from src.domain.value_objects.inspection_status import InspectionStatus
from src.domain.value_objects.version import Version
from src.infrastructure.persistence.sqlalchemy import SQLAlchemyUnitOfWork

NOW = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)


def _make_inspection(user_id: UUID) -> Inspection:
    return Inspection.create(
        id=InspectionId(uuid4()),
        title="Factory Floor",
        location="Building B",
        created_by=UserId(user_id),
        now=NOW,
    )


# ----------------------------------------------------------------------
# get / save (round-trip)
# ----------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestSaveAndGet:
    async def test_save_then_get_round_trip(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        seed_user: UUID,
    ) -> None:
        inspection = _make_inspection(seed_user)
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            await uow.inspections.save(inspection)
            await uow.commit()

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            fetched = await uow.inspections.get(inspection.id)

        assert fetched.id == inspection.id
        assert fetched.title == inspection.title
        assert fetched.location == inspection.location
        assert fetched.status == InspectionStatus.DRAFT
        assert fetched.version == Version(0)
        assert fetched.created_by == inspection.created_by
        assert fetched.created_at == inspection.created_at
        assert fetched.updated_at == inspection.updated_at

    async def test_save_with_observation_and_evidence(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        seed_user: UUID,
    ) -> None:
        inspection = _make_inspection(seed_user)
        obs = inspection.add_observation(
            title="Cracked tile",
            notes="needs repair",
            actor=UserId(seed_user),
            now=NOW,
        )
        inspection.attach_evidence(
            evidence_id=EvidenceId(uuid4()),
            storage_key="evidences/photo.jpg",
            mime_type="image/jpeg",
            file_size_bytes=12345,
            sha256="a" * 64,
            actor=UserId(seed_user),
            now=NOW,
            observation_id=obs.id,
        )

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            await uow.inspections.save(inspection)
            await uow.commit()

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            fetched = await uow.inspections.get(inspection.id)

        assert len(fetched.observations) == 1
        assert fetched.observations[0].title == "Cracked tile"
        assert len(fetched.evidences) == 1
        ev = fetched.evidences[0]
        assert ev.storage_key == "evidences/photo.jpg"
        assert ev.observation_id == obs.id
        assert fetched.version.value == 2  # bumped by add + attach

    async def test_get_missing_raises(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            with pytest.raises(InspectionNotFoundError):
                await uow.inspections.get(InspectionId(uuid4()))

    async def test_exists_returns_true_after_save(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        seed_user: UUID,
    ) -> None:
        inspection = _make_inspection(seed_user)
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            assert await uow.inspections.exists(inspection.id) is False
            await uow.inspections.save(inspection)
            await uow.commit()

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            assert await uow.inspections.exists(inspection.id) is True


# ----------------------------------------------------------------------
# Update flow (re-save replaces children)
# ----------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestUpdate:
    async def test_resave_replaces_observations(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        seed_user: UUID,
    ) -> None:
        inspection = _make_inspection(seed_user)
        inspection.add_observation("first", "n1", UserId(seed_user), NOW)
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            await uow.inspections.save(inspection)
            await uow.commit()

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            loaded = await uow.inspections.get(inspection.id)
            assert len(loaded.observations) == 1
            # Remove the first observation and add a different one.
            loaded.remove_observation(loaded.observations[0].id, UserId(seed_user), NOW)
            loaded.add_observation("second", "n2", UserId(seed_user), NOW)
            await uow.inspections.save(loaded)
            await uow.commit()

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            final = await uow.inspections.get(inspection.id)
        assert len(final.observations) == 1
        assert final.observations[0].title == "second"

    async def test_update_preserves_aggregate_version_bump(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        seed_user: UUID,
    ) -> None:
        inspection = _make_inspection(seed_user)
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            await uow.inspections.save(inspection)
            await uow.commit()

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            loaded = await uow.inspections.get(inspection.id)
            loaded.edit(title="renamed", now=NOW)
            await uow.inspections.save(loaded)
            await uow.commit()

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            final = await uow.inspections.get(inspection.id)
        assert final.title == "renamed"
        assert final.version == Version(1)


# ----------------------------------------------------------------------
# list with filters
# ----------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestList:
    async def test_list_filters_by_status(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        seed_user: UUID,
    ) -> None:
        draft = _make_inspection(seed_user)
        submitted = _make_inspection(seed_user)
        submitted.submit(actor=UserId(seed_user), now=NOW)
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            await uow.inspections.save(draft)
            await uow.inspections.save(submitted)
            await uow.commit()

        from src.application.ports.inspection_repository import InspectionFilters

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            drafts = await uow.inspections.list(
                InspectionFilters(status=InspectionStatus.DRAFT)
            )
            submitteds = await uow.inspections.list(
                InspectionFilters(status=InspectionStatus.SUBMITTED)
            )

        assert {i.id for i in drafts} == {draft.id}
        assert {i.id for i in submitteds} == {submitted.id}

    async def test_list_respects_limit_and_offset(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        seed_user: UUID,
    ) -> None:
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            for _ in range(3):
                await uow.inspections.save(_make_inspection(seed_user))
            await uow.commit()

        from src.application.ports.inspection_repository import InspectionFilters

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            page1 = await uow.inspections.list(InspectionFilters(limit=2, offset=0))
            page2 = await uow.inspections.list(InspectionFilters(limit=2, offset=2))
        assert len(page1) == 2
        assert len(page2) == 1


# ----------------------------------------------------------------------
# UnitOfWork semantics
# ----------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestUnitOfWork:
    async def test_rollback_on_exception(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        seed_user: UUID,
    ) -> None:
        inspection = _make_inspection(seed_user)
        with pytest.raises(RuntimeError):
            async with SQLAlchemyUnitOfWork(session_factory) as uow:
                await uow.inspections.save(inspection)
                raise RuntimeError("boom")

        # Nothing was committed → row does not exist.
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            assert await uow.inspections.exists(inspection.id) is False

    async def test_explicit_rollback_discards_changes(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        seed_user: UUID,
    ) -> None:
        inspection = _make_inspection(seed_user)
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            await uow.inspections.save(inspection)
            await uow.rollback()

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            assert await uow.inspections.exists(inspection.id) is False

    async def test_commit_outside_context_raises(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        uow = SQLAlchemyUnitOfWork(session_factory)
        with pytest.raises(RuntimeError):
            await uow.commit()