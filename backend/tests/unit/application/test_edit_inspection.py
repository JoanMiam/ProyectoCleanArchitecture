"""TDD tests for EditInspection use case."""
from uuid import UUID, uuid4

import pytest

from src.application.dto.create_inspection_dto import CreateInspectionInput
from src.application.dto.edit_inspection_dto import EditInspectionInput
from src.application.use_cases.create_inspection import CreateInspection
from src.application.use_cases.edit_inspection import EditInspection
from src.domain.exceptions import InspectionNotFoundError, InvalidStateError
from src.domain.value_objects.ids import InspectionId, UserId
from tests.unit.conftest import FakeClock, FakeUnitOfWork


@pytest.mark.unit
class TestEditInspection:
    @pytest.fixture
    def fake_uow(self) -> FakeUnitOfWork:
        return FakeUnitOfWork()

    @pytest.fixture
    def fixed_clock(self) -> FakeClock:
        return FakeClock()

    @pytest.fixture
    def use_case(self, fake_uow: FakeUnitOfWork, fixed_clock: FakeClock) -> EditInspection:
        return EditInspection(uow=fake_uow, clock=fixed_clock)

    @pytest.fixture
    def user_id(self) -> UUID:
        return UUID("00000000-0000-0000-0000-000000000001")

    @pytest.fixture
    async def existing_inspection_id(
        self,
        fake_uow: FakeUnitOfWork,
        fixed_clock: FakeClock,
        user_id: UUID,
    ) -> UUID:
        create = CreateInspection(uow=fake_uow, clock=fixed_clock)
        output = await create.execute(
            CreateInspectionInput(title="Original", location="Location A", user_id=user_id)
        )
        fake_uow.committed = False  # reset for test assertions
        return output.inspection_id

    @pytest.mark.asyncio
    async def test_edit_updates_title(
        self,
        use_case: EditInspection,
        existing_inspection_id: UUID,
        user_id: UUID,
        fake_uow: FakeUnitOfWork,
    ) -> None:
        await use_case.execute(
            EditInspectionInput(
                inspection_id=existing_inspection_id,
                user_id=user_id,
                title="Updated Title",
            )
        )
        saved = await fake_uow.inspections.get(InspectionId(existing_inspection_id))
        assert saved.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_edit_updates_location(
        self,
        use_case: EditInspection,
        existing_inspection_id: UUID,
        user_id: UUID,
        fake_uow: FakeUnitOfWork,
    ) -> None:
        await use_case.execute(
            EditInspectionInput(
                inspection_id=existing_inspection_id,
                user_id=user_id,
                location="New Location",
            )
        )
        saved = await fake_uow.inspections.get(InspectionId(existing_inspection_id))
        assert saved.location == "New Location"

    @pytest.mark.asyncio
    async def test_edit_increments_version(
        self,
        use_case: EditInspection,
        existing_inspection_id: UUID,
        user_id: UUID,
        fake_uow: FakeUnitOfWork,
    ) -> None:
        output = await use_case.execute(
            EditInspectionInput(inspection_id=existing_inspection_id, user_id=user_id, title="v1")
        )
        assert output.version == 1

    @pytest.mark.asyncio
    async def test_edit_commits_unit_of_work(
        self,
        use_case: EditInspection,
        existing_inspection_id: UUID,
        user_id: UUID,
        fake_uow: FakeUnitOfWork,
    ) -> None:
        await use_case.execute(
            EditInspectionInput(inspection_id=existing_inspection_id, user_id=user_id, title="x")
        )
        assert fake_uow.committed is True

    @pytest.mark.asyncio
    async def test_edit_nonexistent_inspection_raises(
        self,
        use_case: EditInspection,
        user_id: UUID,
    ) -> None:
        with pytest.raises(InspectionNotFoundError):
            await use_case.execute(
                EditInspectionInput(inspection_id=uuid4(), user_id=user_id, title="x")
            )

    @pytest.mark.asyncio
    async def test_edit_closed_inspection_raises(
        self,
        use_case: EditInspection,
        existing_inspection_id: UUID,
        user_id: UUID,
        fake_uow: FakeUnitOfWork,
    ) -> None:
        inspection = await fake_uow.inspections.get(InspectionId(existing_inspection_id))
        inspection.submit(actor=UserId(user_id), now=use_case._clock.now())
        inspection.close(actor=UserId(user_id), now=use_case._clock.now())
        await fake_uow.inspections.save(inspection)

        with pytest.raises(InvalidStateError):
            await use_case.execute(
                EditInspectionInput(
                    inspection_id=existing_inspection_id, user_id=user_id, title="fail")
            )
