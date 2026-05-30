from __future__ import annotations

from dataclasses import fields as dc_fields
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.audit_dto import AuditEntryDTO
from src.application.ports.audit_repository import AuditRepository
from src.domain.events import DomainEvent
from src.domain.value_objects.ids import InspectionId
from src.infrastructure.persistence.sqlalchemy.models.audit_event_model import AuditEventModel

_ACTOR_FIELDS = (
    "created_by",
    "submitted_by",
    "closed_by",
    "added_by",
    "edited_by",
    "removed_by",
    "attached_by",
)


def _serialize_event(event: DomainEvent) -> AuditEventModel:
    """Extract structured columns + JSON payload from any DomainEvent."""
    all_fields: dict[str, Any] = {
        f.name: getattr(event, f.name) for f in dc_fields(event)
    }
    occurred_at: datetime = all_fields.pop("occurred_at")
    # ensure UTC-aware for PostgreSQL DateTime(timezone=True)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)

    aggregate_id: UUID = all_fields.pop("inspection_id", None)

    actor_id: UUID | None = None
    for af in _ACTOR_FIELDS:
        if af in all_fields:
            actor_id = all_fields.pop(af)
            break

    payload = {k: str(v) if isinstance(v, UUID) else v for k, v in all_fields.items()}

    return AuditEventModel(
        aggregate_id=aggregate_id,
        aggregate_type="Inspection",
        event_type=type(event).__name__,
        actor_id=actor_id,
        payload=payload,
        occurred_at=occurred_at,
    )


def _model_to_dto(model: AuditEventModel) -> AuditEntryDTO:
    occurred_at = model.occurred_at
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    return AuditEntryDTO(
        aggregate_id=model.aggregate_id,
        aggregate_type=model.aggregate_type,
        event_type=model.event_type,
        actor_id=model.actor_id,
        occurred_at=occurred_at,
        payload=model.payload,
    )


class SQLAlchemyAuditRepository(AuditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: DomainEvent) -> None:
        self._session.add(_serialize_event(event))

    async def append_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            self._session.add(_serialize_event(event))

    async def list_for_inspection(
        self, inspection_id: InspectionId
    ) -> list[AuditEntryDTO]:
        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.aggregate_id == inspection_id)
            .order_by(AuditEventModel.occurred_at.asc(), AuditEventModel.id.asc())
        )
        result = await self._session.execute(stmt)
        return [_model_to_dto(m) for m in result.scalars().all()]
