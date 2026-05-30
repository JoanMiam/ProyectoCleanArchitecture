"""TDD tests for SubmitInspection use case."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.application.dto.submit_inspection_dto import SubmitInspectionInput
from src.application.use_cases.submit_inspection import SubmitInspection
from src.domain.entities.inspection import Inspection
from src.domain.exceptions import InvalidStateError
from src.domain.value_objects.ids import InspectionId, UserId
from src.domain.value_objects.inspection_status import InspectionStatus
from tests.unit.conftest import FakeClock, FakeUnitOfWork


def _make_inspection(created_by: UUID, *, closed: bool = False) -> Inspection:
    now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    inspection = Inspection.create(
        id=InspectionId(uuid4()),
        title="Inspection",
        location="Site",
        created_by=UserId(created_by),
        now=now,
    )
    if closed:
        inspection.submit(actor=UserId(created_by), now=now)
        inspection.close(actor=UserId(created_by), now=now)
    return inspection


@pytest.mark.unit
class TestSubmitInspection:
    @pytest.fixture
    def use_case(self, fake_uow: FakeUnitOfWork, fixed_clock: FakeClock) -> SubmitInspection:
        return SubmitInspection(uow=fake_uow, clock=fixed_clock)

    @pytest.mark.asyncio
    async def test_submits_draft_inspection(
        self, use_case: SubmitInspection, fake_uow: FakeUnitOfWork, user_id: UUID
    ) -> None:
        inspection = _make_inspection(user_id)
        await fake_uow.inspections.save(inspection)

        output = await use_case.execute(
            SubmitInspectionInput(inspection_id=inspection.id, user_id=user_id)
        )

        assert output.status == InspectionStatus.SUBMITTED
        assert output.version == 1
        assert fake_uow.committed is True

    @pytest.mark.asyncio
    async def test_rejects_when_not_submittable(
        self, use_case: SubmitInspection, fake_uow: FakeUnitOfWork, user_id: UUID
    ) -> None:
        inspection = _make_inspection(user_id, closed=True)
        await fake_uow.inspections.save(inspection)

        with pytest.raises(InvalidStateError):
            await use_case.execute(
                SubmitInspectionInput(inspection_id=inspection.id, user_id=user_id)
            )
