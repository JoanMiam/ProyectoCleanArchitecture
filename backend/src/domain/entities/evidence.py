from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.value_objects.ids import EvidenceId, InspectionId, ObservationId


@dataclass(frozen=True)
class Evidence:
    """Immutable reference to a stored file. Belongs to an Inspection (optionally to an Observation)."""

    id: EvidenceId
    inspection_id: InspectionId
    observation_id: ObservationId | None
    storage_key: str
    mime_type: str
    file_size_bytes: int
    sha256: str
    uploaded_at: datetime
