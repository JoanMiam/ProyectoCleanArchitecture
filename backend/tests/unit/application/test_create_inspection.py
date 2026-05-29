"""TDD tests for CreateInspection use case."""
from uuid import UUID

import pytest

from src.application.dto.create_inspection_dto import CreateInspectionInput
from src.application.use_cases.create_inspection import CreateInspection
from src.domain.value_objects.inspection_status import InspectionStatus
from src.domain.value_objects.version import Version
from tests.unit.conftest import FakeClock, FakeUnitOfWork


@pytest.mark.unit
class TestCreateInspection:
    @pytest.fixture
    def use_case(self, fake_uow: FakeUnitOfWork, fixed_clock: FakeClock) -> CreateInspection:
        return CreateInspection(uow=fake_uow, clock=fixed_clock)

    @pytest.fixture
    def valid_input(self, user_id: UUID) -> CreateInspectionInput:
        return CreateInspectionInput(
            title="Factory Floor Inspection",
            location="Building B, Floor 2",
            user_id=user_id,
        )

    @pytest.mark.asyncio
    async def test_creates_inspection_with_draft_status(
        self,
        use_case: CreateInspection,
        valid_input: CreateInspectionInput,
    ) -> None:
        await use_case.execute(valid_input)
        saved = use_case._uow.inspections.saved[0]  # type: ignore[attr-defined]
        assert saved.status == InspectionStatus.DRAFT

    @pytest.mark.asyncio
    async def test_creates_inspection_with_version_zero(
        self,
        use_case: CreateInspection,
        valid_input: CreateInspectionInput,
    ) -> None:
        await use_case.execute(valid_input)
        saved = use_case._uow.inspections.saved[0]  # type: ignore[attr-defined]
        assert saved.version == Version(0)

    @pytest.mark.asyncio
    async def test_output_contains_new_inspection_id(
        self,
        use_case: CreateInspection,
        valid_input: CreateInspectionInput,
    ) -> None:
        output = await use_case.execute(valid_input)
        assert output.inspection_id is not None

    @pytest.mark.asyncio
    async def test_saves_to_repository(
        self,
        use_case: CreateInspection,
        valid_input: CreateInspectionInput,
        fake_uow: FakeUnitOfWork,
    ) -> None:
        await use_case.execute(valid_input)
        assert len(fake_uow.inspections.saved) == 1

    @pytest.mark.asyncio
    async def test_commits_unit_of_work(
        self,
        use_case: CreateInspection,
        valid_input: CreateInspectionInput,
        fake_uow: FakeUnitOfWork,
    ) -> None:
        await use_case.execute(valid_input)
        assert fake_uow.committed is True

    @pytest.mark.asyncio
    async def test_output_version_is_zero(
        self,
        use_case: CreateInspection,
        valid_input: CreateInspectionInput,
    ) -> None:
        output = await use_case.execute(valid_input)
        assert output.version == 0

    @pytest.mark.asyncio
    async def test_output_status_is_draft(
        self,
        use_case: CreateInspection,
        valid_input: CreateInspectionInput,
    ) -> None:
        output = await use_case.execute(valid_input)
        assert output.status == InspectionStatus.DRAFT
