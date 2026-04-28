from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class EditInspectionInput:
    inspection_id: UUID
    user_id: UUID
    title: str | None = None
    location: str | None = None


@dataclass(frozen=True)
class EditInspectionOutput:
    inspection_id: UUID
    version: int
    status: str
