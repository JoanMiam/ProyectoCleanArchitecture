"""ORM model for the ``inspections`` table (aggregate root).

Children (observations, evidences) are mapped with ``cascade="all, delete-orphan"``
so the repository can replace them atomically when saving the aggregate.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.sqlalchemy.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.persistence.sqlalchemy.models.evidence_model import EvidenceModel
    from src.infrastructure.persistence.sqlalchemy.models.observation_model import (
        ObservationModel,
    )


class InspectionModel(Base):
    __tablename__ = "inspections"
    __table_args__ = (
        Index("ix_inspections_created_by", "created_by"),
        Index("ix_inspections_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    observations: Mapped[list[ObservationModel]] = relationship(
        "ObservationModel",
        back_populates="inspection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    evidences: Mapped[list[EvidenceModel]] = relationship(
        "EvidenceModel",
        back_populates="inspection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )