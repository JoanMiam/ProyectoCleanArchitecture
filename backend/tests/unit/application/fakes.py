from types import TracebackType
from typing import Self
from uuid import UUID

from src.application.dto.sync_dto import AppliedChangeDTO
from src.application.ports.changeset_repository import ChangeSetRepository
from src.application.ports.inspection_repository import InspectionFilters, InspectionRepository
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.entities.inspection import Inspection
from src.domain.value_objects.ids import InspectionId


class FakeInspectionRepository(InspectionRepository):
    def __init__(self) -> None:
        self.inspections: dict[InspectionId, Inspection] = {}

    async def get(self, id: InspectionId) -> Inspection:
        if id not in self.inspections:
            raise ValueError(f"Inspection {id} not found")
        return self.inspections[id]

    async def save(self, inspection: Inspection) -> None:
        self.inspections[inspection.id] = inspection

    async def list(self, filters: InspectionFilters | None = None) -> list[Inspection]:
        return list(self.inspections.values())

    async def exists(self, id: InspectionId) -> bool:
        return id in self.inspections


class FakeChangeSetRepository(ChangeSetRepository):
    def __init__(self) -> None:
        self.applied: dict[UUID, AppliedChangeDTO] = {}

    async def has_been_applied(self, change_id: UUID) -> bool:
        return change_id in self.applied

    async def record_applied(self, applied: AppliedChangeDTO) -> None:
        self.applied[applied.change_id] = applied

    async def get_applied(self, change_id: UUID) -> AppliedChangeDTO | None:
        return self.applied.get(change_id)


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.inspections = FakeInspectionRepository()
        self.changesets = FakeChangeSetRepository()  # Non-standard port access for testing
        self.committed = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type:
            await self.rollback()
