"""TDD tests for ListInspections use case."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.application.dto.list_inspections_dto import ListInspectionsInput
from src.application.use_cases.list_inspections import ListInspections
from src.domain.entities.inspection import Inspection
from src.domain.value_objects.ids import InspectionId, UserId
from src.domain.value_objects.inspection_status import InspectionStatus
from tests.unit.conftest import FakeUnitOfWork


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
class TestListInspections:
    @pytest.fixture
    def use_case(self, fake_uow: FakeUnitOfWork) -> ListInspections:
        return ListInspections(uow=fake_uow)

    @pytest.mark.asyncio
    async def test_returns_all_inspections(
        self, use_case: ListInspections, fake_uow: FakeUnitOfWork, user_id: UUID
    ) -> None:
        await fake_uow.inspections.save(_make_inspection(user_id))
        await fake_uow.inspections.save(_make_inspection(user_id))

        output = await use_case.execute(ListInspectionsInput())

        assert output.count == 2
        assert len(output.items) == 2

    @pytest.mark.asyncio
    async def test_filters_by_status(
        self, use_case: ListInspections, fake_uow: FakeUnitOfWork, user_id: UUID
    ) -> None:
        await fake_uow.inspections.save(_make_inspection(user_id))
        await fake_uow.inspections.save(_make_inspection(user_id, submitted=True))

        output = await use_case.execute(
            ListInspectionsInput(status=InspectionStatus.SUBMITTED)
        )

        assert output.count == 1
        assert output.items[0].status == InspectionStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_returns_empty_when_none_match(
        self, use_case: ListInspections
    ) -> None:
        output = await use_case.execute(ListInspectionsInput())
        assert output.count == 0
        assert output.items == []
