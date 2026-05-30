from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AddObservationInput:
    inspection_id: UUID
    user_id: UUID
    title: str
    notes: str


@dataclass(frozen=True)
class AddObservationOutput:
    inspection_id: UUID
    observation_id: UUID
    version: int
