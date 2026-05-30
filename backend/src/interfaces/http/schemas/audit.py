from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditEntryResponse(BaseModel):
    aggregate_id: UUID
    aggregate_type: str
    event_type: str
    actor_id: UUID | None
    occurred_at: datetime
    payload: dict[str, Any]


class AuditTrailResponse(BaseModel):
    inspection_id: UUID
    entries: list[AuditEntryResponse]
    count: int
