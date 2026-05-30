from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ListInspectionsInput:
    status: str | None = None
    created_by: UUID | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class InspectionSummary:
    inspection_id: UUID
    title: str
    location: str
    status: str
    version: int


@dataclass(frozen=True)
class ListInspectionsOutput:
    items: list[InspectionSummary]
    count: int
