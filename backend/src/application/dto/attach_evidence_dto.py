from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AttachEvidenceInput:
    inspection_id: UUID
    user_id: UUID
    filename: str
    mime_type: str
    content: bytes
    observation_id: UUID | None = None


@dataclass(frozen=True)
class AttachEvidenceOutput:
    inspection_id: UUID
    evidence_id: UUID
    observation_id: UUID | None
    storage_key: str
    mime_type: str
    file_size_bytes: int
    sha256: str
    version: int
