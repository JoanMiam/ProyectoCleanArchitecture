from uuid import UUID

from pydantic import BaseModel

from src.application.dto.attach_evidence_dto import AttachEvidenceOutput


class EvidenceResponse(BaseModel):
    inspection_id: UUID
    evidence_id: UUID
    observation_id: UUID | None
    storage_key: str
    mime_type: str
    file_size_bytes: int
    sha256: str
    version: int

    @classmethod
    def from_output(cls, output: AttachEvidenceOutput) -> "EvidenceResponse":
        return cls(
            inspection_id=output.inspection_id,
            evidence_id=output.evidence_id,
            observation_id=output.observation_id,
            storage_key=output.storage_key,
            mime_type=output.mime_type,
            file_size_bytes=output.file_size_bytes,
            sha256=output.sha256,
            version=output.version,
        )
