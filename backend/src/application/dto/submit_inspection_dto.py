from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SubmitInspectionInput:
    inspection_id: UUID
    user_id: UUID


@dataclass(frozen=True)
class SubmitInspectionOutput:
    inspection_id: UUID
    status: str
    version: int
