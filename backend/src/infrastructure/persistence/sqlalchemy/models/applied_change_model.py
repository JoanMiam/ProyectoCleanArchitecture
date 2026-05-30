"""ORM model for applied sync changes."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Integer, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.infrastructure.persistence.sqlalchemy.models.base import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


class AppliedChangeModel(Base):
    __tablename__ = "applied_changes"

    change_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    new_version: Mapped[int] = mapped_column(Integer, nullable=False)
    server_delta: Mapped[dict[str, Any]] = mapped_column(
        JsonType,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
