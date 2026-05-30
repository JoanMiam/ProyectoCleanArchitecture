"""ORM model for the ``observations`` table (child of Inspection)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.sqlalchemy.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.persistence.sqlalchemy.models.inspection_model import InspectionModel


class ObservationModel(Base):
    __tablename__ = "observations"
    __table_args__ = (Index("ix_observations_inspection_id", "inspection_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    inspection_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    inspection: Mapped[InspectionModel] = relationship(
        "InspectionModel", back_populates="observations"
    )