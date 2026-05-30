"""ORM model for the ``audit_events`` append-only log.

The concrete ``AuditRepository`` adapter that uses this model lives in INS-10.
The model is defined here so ``Base.metadata`` matches alembic 0001.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.infrastructure.persistence.sqlalchemy.models.base import Base

# JSONB on PostgreSQL, JSON on every other dialect (SQLite for tests).
JsonType = JSON().with_variant(JSONB(), "postgresql")

# SQLite only autoincrements INTEGER PRIMARY KEY, not BIGINT.
_BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_aggregate_id", "aggregate_id", "occurred_at"),)

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)