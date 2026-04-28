from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CreateInspectionInput:
    title: str
    location: str
    user_id: UUID


@dataclass(frozen=True)
class CreateInspectionOutput:
    inspection_id: UUID
    version: int
    status: str
