"""TDD tests for GetInspection use case."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.application.dto.get_inspection_dto import GetInspectionInput
from src.application.use_cases.get_inspection import GetInspection
from src.domain.entities.inspection import Inspection
from src.domain.exceptions import InspectionNotFoundError
from src.domain.value_objects.ids import InspectionId, UserId
from tests.unit.conftest import FakeUnitOfWork


def _make_inspection(created_by: UUID) -> Inspection:
    now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    inspection = Inspection.create(
        id=InspectionId(uuid4()),
        title="Roof Inspection",
        location="Warehouse A",
        created_by=UserId(created_by),
        now=now,
    )
    inspection.add_observation(title="Crack", notes="North wall", actor=UserId(created_by), now=now)
    return inspection


@pytest.mark.unit
class TestGetInspection:
    @pytest.fixture
    def use_case(self, fake_uow: FakeUnitOfWork) -> GetInspection:
        return GetInspection(uow=fake_uow)

    @pytest.mark.asyncio
    async def test_returns_inspection_details(
        self, use_case: GetInspection, fake_uow: FakeUnitOfWork, user_id: UUID
    ) -> None:
        inspection = _make_inspection(user_id)
        await fake_uow.inspections.save(inspection)

        output = await use_case.execute(GetInspectionInput(inspection_id=inspection.id))

        assert output.inspection_id == inspection.id
        assert output.title == "Roof Inspection"
        assert output.location == "Warehouse A"
        assert output.created_by == user_id

    @pytest.mark.asyncio
    async def test_includes_observations(
        self, use_case: GetInspection, fake_uow: FakeUnitOfWork, user_id: UUID
    ) -> None:
        inspection = _make_inspection(user_id)
        await fake_uow.inspections.save(inspection)

        output = await use_case.execute(GetInspectionInput(inspection_id=inspection.id))

        assert len(output.observations) == 1
        assert output.observations[0].title == "Crack"
        assert output.evidence_count == 0

    @pytest.mark.asyncio
    async def test_raises_when_inspection_missing(self, use_case: GetInspection) -> None:
        with pytest.raises(InspectionNotFoundError):
            await use_case.execute(GetInspectionInput(inspection_id=uuid4()))
