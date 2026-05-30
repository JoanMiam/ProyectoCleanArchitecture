from src.application.dto.submit_inspection_dto import (
    SubmitInspectionInput,
    SubmitInspectionOutput,
)
from src.application.ports.clock import Clock
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.value_objects.ids import InspectionId, UserId


class SubmitInspection:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, cmd: SubmitInspectionInput) -> SubmitInspectionOutput:
        async with self._uow:
            inspection = await self._uow.inspections.get(InspectionId(cmd.inspection_id))
            inspection.submit(actor=UserId(cmd.user_id), now=self._clock.now())
            await self._uow.inspections.save(inspection)
            await self._uow.commit()
            return SubmitInspectionOutput(
                inspection_id=inspection.id,
                status=inspection.status,
                version=inspection.version.value,
            )
