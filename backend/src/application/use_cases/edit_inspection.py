from src.application.dto.edit_inspection_dto import EditInspectionInput, EditInspectionOutput
from src.application.ports.clock import Clock
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.value_objects.ids import InspectionId


class EditInspection:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, cmd: EditInspectionInput) -> EditInspectionOutput:
        async with self._uow:
            inspection = await self._uow.inspections.get(InspectionId(cmd.inspection_id))
            inspection.edit(
                title=cmd.title,
                location=cmd.location,
                now=self._clock.now(),
            )
            await self._uow.inspections.save(inspection)
            await self._uow.commit()
            return EditInspectionOutput(
                inspection_id=inspection.id,
                version=inspection.version.value,
                status=inspection.status,
            )
