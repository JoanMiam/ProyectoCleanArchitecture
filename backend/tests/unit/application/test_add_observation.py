"""TDD tests for AddObservation use case."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.application.dto.add_observation_dto import AddObservationInput
from src.application.use_cases.add_observation import AddObservation
from src.domain.entities.inspection import Inspection
from src.domain.exceptions import InvalidStateError
from src.domain.value_objects.ids import InspectionId, UserId
from tests.unit.conftest import FakeClock, FakeUnitOfWork


def _make_inspection(created_by: UUID, *, submitted: bool = False) -> Inspection:
    now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    inspection = Inspection.create(
        id=InspectionId(uuid4()),
        title="Inspection",
        location="Site",
        created_by=UserId(created_by),
        now=now,
    )
    if submitted:
        inspection.submit(actor=UserId(created_by), now=now)
    return inspection


@pytest.mark.unit
class TestAddObservation:
    @pytest.fixture
    def use_case(self, fake_uow: FakeUnitOfWork, fixed_clock: FakeClock) -> AddObservation:
        return AddObservation(uow=fake_uow, clock=fixed_clock)

    @pytest.mark.asyncio
    async def test_adds_observation_and_bumps_version(
        self, use_case: AddObservation, fake_uow: FakeUnitOfWork, user_id: UUID
    ) -> None:
        inspection = _make_inspection(user_id)
        await fake_uow.inspections.save(inspection)

        output = await use_case.execute(
            AddObservationInput(
                inspection_id=inspection.id,
                user_id=user_id,
                title="Crack",
                notes="North wall",
            )
        )

        assert output.observation_id is not None
        assert output.version == 1

    @pytest.mark.asyncio
    async def test_persists_and_commits(
        self, use_case: AddObservation, fake_uow: FakeUnitOfWork, user_id: UUID
    ) -> None:
        inspection = _make_inspection(user_id)
        await fake_uow.inspections.save(inspection)

        await use_case.execute(
            AddObservationInput(
                inspection_id=inspection.id, user_id=user_id, title="A", notes="B"
            )
        )

        assert fake_uow.committed is True
        assert len(fake_uow.inspections._store[inspection.id].observations) == 1

    @pytest.mark.asyncio
    async def test_rejects_when_inspection_not_editable(
        self, use_case: AddObservation, fake_uow: FakeUnitOfWork, user_id: UUID
    ) -> None:
        inspection = _make_inspection(user_id, submitted=True)
        await fake_uow.inspections.save(inspection)

        with pytest.raises(InvalidStateError):
            await use_case.execute(
                AddObservationInput(
                    inspection_id=inspection.id, user_id=user_id, title="A", notes="B"
                )
            )
