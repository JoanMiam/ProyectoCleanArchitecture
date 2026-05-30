"""ORM model for the ``evidences`` table (child of Inspection)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.sqlalchemy.models.base import Base

if TYPE_CHECKING:
    from src.infrastructure.persistence.sqlalchemy.models.inspection_model import InspectionModel


class EvidenceModel(Base):
    __tablename__ = "evidences"
    __table_args__ = (Index("ix_evidences_inspection_id", "inspection_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    inspection_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    observation_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("observations.id", ondelete="SET NULL"), nullable=True
    )
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    inspection: Mapped[InspectionModel] = relationship(
        "InspectionModel", back_populates="evidences"
    )