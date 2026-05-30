from abc import ABC, abstractmethod

from src.application.dto.audit_dto import AuditEntryDTO
from src.domain.events import DomainEvent
from src.domain.value_objects.ids import InspectionId


class AuditRepository(ABC):
    """Append-only log of domain events for traceability.

    Events are never updated or deleted; they record who changed what and when.
    Stored events back the audit trail and read-model projections (INS-10).
    """

    @abstractmethod
    async def append(self, event: DomainEvent) -> None: ...

    @abstractmethod
    async def append_many(self, events: list[DomainEvent]) -> None: ...

    @abstractmethod
    async def list_for_inspection(
        self, inspection_id: InspectionId
    ) -> list[AuditEntryDTO]: ...
