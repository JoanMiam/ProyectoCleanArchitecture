from uuid import uuid4

from src.application.dto.create_inspection_dto import CreateInspectionInput, CreateInspectionOutput
from src.application.ports.clock import Clock
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.entities.inspection import Inspection
from src.domain.value_objects.ids import InspectionId, UserId


class CreateInspection:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, cmd: CreateInspectionInput) -> CreateInspectionOutput:
        async with self._uow:
            inspection = Inspection.create(
                id=InspectionId(uuid4()),
                title=cmd.title,
                location=cmd.location,
                created_by=UserId(cmd.user_id),
                now=self._clock.now(),
            )
            await self._uow.inspections.save(inspection)
            await self._uow.commit()
            return CreateInspectionOutput(
                inspection_id=inspection.id,
                version=inspection.version.value,
                status=inspection.status,
            )
