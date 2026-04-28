from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.inspection import Inspection
from src.domain.value_objects.ids import InspectionId
from src.domain.value_objects.inspection_status import InspectionStatus


@dataclass
class InspectionFilters:
    status: InspectionStatus | None = None
    created_by: UUID | None = None
    limit: int = 50
    offset: int = 0


class InspectionRepository(ABC):
    @abstractmethod
    async def get(self, id: InspectionId) -> Inspection: ...

    @abstractmethod
    async def save(self, inspection: Inspection) -> None: ...

    @abstractmethod
    async def list(self, filters: InspectionFilters | None = None) -> list[Inspection]: ...

    @abstractmethod
    async def exists(self, id: InspectionId) -> bool: ...
