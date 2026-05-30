from src.application.dto.list_inspections_dto import (
    InspectionSummary,
    ListInspectionsInput,
    ListInspectionsOutput,
)
from src.application.ports.inspection_repository import InspectionFilters
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.value_objects.inspection_status import InspectionStatus


class ListInspections:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListInspectionsInput) -> ListInspectionsOutput:
        filters = InspectionFilters(
            status=InspectionStatus(query.status) if query.status is not None else None,
            created_by=query.created_by,
            limit=query.limit,
            offset=query.offset,
        )
        async with self._uow:
            inspections = await self._uow.inspections.list(filters)
            items = [
                InspectionSummary(
                    inspection_id=i.id,
                    title=i.title,
                    location=i.location,
                    status=i.status,
                    version=i.version.value,
                )
                for i in inspections
            ]
            return ListInspectionsOutput(items=items, count=len(items))
