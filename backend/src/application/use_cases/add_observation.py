from __future__ import annotations

from src.application.dto.add_observation_dto import AddObservationInput, AddObservationOutput
from src.application.ports.audit_repository import AuditRepository
from src.application.ports.clock import Clock
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.value_objects.ids import InspectionId, UserId


class AddObservation:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        audit_repo: AuditRepository | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._audit_repo = audit_repo

    async def execute(self, cmd: AddObservationInput) -> AddObservationOutput:
        async with self._uow:
            inspection = await self._uow.inspections.get(InspectionId(cmd.inspection_id))
            observation = inspection.add_observation(
                title=cmd.title,
                notes=cmd.notes,
                actor=UserId(cmd.user_id),
                now=self._clock.now(),
            )
            await self._uow.inspections.save(inspection)
            await self._uow.commit()

        if self._audit_repo is not None:
            events = inspection.collect_events()
            if events:
                await self._audit_repo.append_many(events)

        return AddObservationOutput(
            inspection_id=inspection.id,
            observation_id=observation.id,
            version=inspection.version.value,
        )
