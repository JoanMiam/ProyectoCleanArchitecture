from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.value_objects.ids import InspectionId, ObservationId
from src.domain.value_objects.version import Version


@dataclass
class Observation:
    id: ObservationId
    inspection_id: InspectionId
    title: str
    notes: str
    version: Version
    created_at: datetime
    updated_at: datetime

    def edit(self, title: str | None = None, notes: str | None = None) -> None:
        if title is not None:
            self.title = title
        if notes is not None:
            self.notes = notes
        self.version = self.version.increment()
