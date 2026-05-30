from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class AuditEntryDTO:
    aggregate_id: UUID
    aggregate_type: str
    event_type: str
    actor_id: UUID | None
    occurred_at: datetime
    payload: dict[str, Any]
