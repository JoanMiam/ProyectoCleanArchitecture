"""RQ worker job: persist a single serialized audit event to the DB.

Called via QueueGateway.enqueue("interfaces.workers.audit_worker.record_audit_event", data).
The payload dict must match the columns of AuditEventModel.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.infrastructure.persistence.sqlalchemy.models.audit_event_model import AuditEventModel
from src.infrastructure.persistence.sqlalchemy.session import get_session_factory


def record_audit_event(data: dict[str, Any]) -> None:
    """RQ entry point — runs synchronously in the worker process."""
    asyncio.run(_async_record(data))


async def _async_record(data: dict[str, Any]) -> None:
    occurred_at = datetime.fromisoformat(data["occurred_at"])
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)

    factory = get_session_factory()
    async with factory() as session:
        session.add(
            AuditEventModel(
                aggregate_id=UUID(data["aggregate_id"]),
                aggregate_type=data["aggregate_type"],
                event_type=data["event_type"],
                actor_id=UUID(data["actor_id"]) if data.get("actor_id") else None,
                payload=data.get("payload", {}),
                occurred_at=occurred_at,
            )
        )
        await session.commit()
