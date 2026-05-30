from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.dto.audit_dto import AuditEntryDTO
from src.application.ports.audit_repository import AuditRepository
from src.domain.value_objects.ids import InspectionId


@dataclass(frozen=True)
class GetAuditTrailInput:
    inspection_id: UUID


@dataclass(frozen=True)
class GetAuditTrailOutput:
    entries: list[AuditEntryDTO]


class GetAuditTrail:
    def __init__(self, audit_repo: AuditRepository) -> None:
        self._audit = audit_repo

    async def execute(self, query: GetAuditTrailInput) -> GetAuditTrailOutput:
        entries = await self._audit.list_for_inspection(InspectionId(query.inspection_id))
        return GetAuditTrailOutput(entries=entries)
