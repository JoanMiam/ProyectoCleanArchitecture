from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetInspectionInput:
    inspection_id: UUID


@dataclass(frozen=True)
class ObservationView:
    observation_id: UUID
    title: str
    notes: str
    version: int


@dataclass(frozen=True)
class GetInspectionOutput:
    inspection_id: UUID
    title: str
    location: str
    status: str
    version: int
    created_by: UUID
    observations: list[ObservationView]
    evidence_count: int
