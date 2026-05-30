"""SQLAlchemy-backed implementation of :class:`InspectionRepository`.
 
Save strategy: a domain aggregate is the unit of persistence. On save we either
INSERT the whole aggregate (root + children) or UPDATE the root and replace its
children with a fresh set produced by the mapper. The cascade configured on the
``InspectionModel`` relationships takes care of deleting orphaned rows.
"""
 
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.inspection_repository import InspectionFilters, InspectionRepository
from src.domain.entities.inspection import Inspection
from src.domain.exceptions import InspectionNotFoundError
from src.domain.value_objects.ids import InspectionId
from src.infrastructure.persistence.sqlalchemy.mappers.inspection_mapper import (
    evidence_to_model,
    inspection_to_domain,
    inspection_to_model,
    observation_to_model,
)
from src.infrastructure.persistence.sqlalchemy.models.inspection_model import InspectionModel
 
 
class SQLAlchemyInspectionRepository(InspectionRepository):
    """Persist and read :class:`Inspection` aggregates via SQLAlchemy.
 
    The repository never opens or closes a transaction: that is the UnitOfWork's
    job. It only issues statements on the provided session.
    """
 
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
 
    # ------------------------------------------------------------------
 
    async def get(self, id: InspectionId) -> Inspection:
        model = await self._session.get(InspectionModel, id)
        if model is None:
            raise InspectionNotFoundError(f"Inspection '{id}' not found.")
        return inspection_to_domain(model)
 
    async def exists(self, id: InspectionId) -> bool:
        # SELECT 1 ... LIMIT 1 — avoids hydrating children.
        stmt = select(InspectionModel.id).where(InspectionModel.id == id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
 
    async def list(self, filters: InspectionFilters | None = None) -> list[Inspection]:
        stmt = select(InspectionModel)
        if filters is not None:
            if filters.status is not None:
                stmt = stmt.where(InspectionModel.status == filters.status.value)
            if filters.created_by is not None:
                stmt = stmt.where(InspectionModel.created_by == filters.created_by)
            stmt = stmt.order_by(InspectionModel.created_at.desc())
            stmt = stmt.limit(filters.limit).offset(filters.offset)
        else:
            stmt = stmt.order_by(InspectionModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [inspection_to_domain(m) for m in models]
 
    # ------------------------------------------------------------------
 
    async def save(self, inspection: Inspection) -> None:
        """Insert a new aggregate or replace an existing one (root + children).
 
        We load the existing row when present so SQLAlchemy emits an UPDATE
        instead of a duplicate-key INSERT. Children are reassigned from the
        mapper's output; ``cascade="all, delete-orphan"`` deletes the previous
        children automatically on flush.
        """
        existing = await self._session.get(InspectionModel, inspection.id)
        if existing is None:
            self._session.add(inspection_to_model(inspection))
            return
        try:
            self._update_existing(existing, inspection)
        except NoResultFound as exc:  # pragma: no cover — defensive
            raise InspectionNotFoundError(str(inspection.id)) from exc
 
    @staticmethod
    def _update_existing(existing: InspectionModel, inspection: Inspection) -> None:
        existing.title = inspection.title
        existing.location = inspection.location
        existing.status = inspection.status.value
        existing.version = inspection.version.value
        existing.updated_at = inspection.updated_at
        # Replace children — cascade="all, delete-orphan" removes the old ones.
        existing.observations = [observation_to_model(o) for o in inspection.observations]
        existing.evidences = [evidence_to_model(e) for e in inspection.evidences]
