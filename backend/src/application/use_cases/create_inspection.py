from __future__ import annotations

from uuid import uuid4

from src.application.dto.create_inspection_dto import CreateInspectionInput, CreateInspectionOutput
from src.application.ports.audit_repository import AuditRepository
from src.application.ports.clock import Clock
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.entities.inspection import Inspection
from src.domain.value_objects.ids import InspectionId, UserId


class CreateInspection:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        audit_repo: AuditRepository | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._audit_repo = audit_repo

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

        if self._audit_repo is not None:
            events = inspection.collect_events()
            if events:
                await self._audit_repo.append_many(events)

        return CreateInspectionOutput(
            inspection_id=inspection.id,
            version=inspection.version.value,
            status=inspection.status,
        )
