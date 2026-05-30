from src.application.dto.get_inspection_dto import (
    GetInspectionInput,
    GetInspectionOutput,
    ObservationView,
)
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.value_objects.ids import InspectionId


class GetInspection:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetInspectionInput) -> GetInspectionOutput:
        async with self._uow:
            inspection = await self._uow.inspections.get(InspectionId(query.inspection_id))
            return GetInspectionOutput(
                inspection_id=inspection.id,
                title=inspection.title,
                location=inspection.location,
                status=inspection.status,
                version=inspection.version.value,
                created_by=inspection.created_by,
                observations=[
                    ObservationView(
                        observation_id=obs.id,
                        title=obs.title,
                        notes=obs.notes,
                        version=obs.version.value,
                    )
                    for obs in inspection.observations
                ],
                evidence_count=len(inspection.evidences),
            )
