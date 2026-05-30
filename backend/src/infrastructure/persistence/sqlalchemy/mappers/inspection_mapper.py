"""Pure mappers between domain entities and ORM models.

Mappers are stateless functions: no session, no I/O. They live in infrastructure
because they know both sides, but the domain has no idea they exist.
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.domain.entities.evidence import Evidence
from src.domain.entities.inspection import Inspection
from src.domain.entities.observation import Observation
from src.domain.value_objects.ids import (
    EvidenceId,
    InspectionId,
    ObservationId,
    UserId,
)
from src.domain.value_objects.inspection_status import InspectionStatus
from src.domain.value_objects.version import Version
from src.infrastructure.persistence.sqlalchemy.models.evidence_model import EvidenceModel
from src.infrastructure.persistence.sqlalchemy.models.inspection_model import InspectionModel
from src.infrastructure.persistence.sqlalchemy.models.observation_model import ObservationModel


def _as_utc(value: datetime) -> datetime:
    """Force tz-aware UTC.

    Columns are declared ``DateTime(timezone=True)``; PostgreSQL hands us aware
    datetimes, SQLite hands us naive ones. The domain always expects aware
    datetimes, so we normalize at the boundary.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)

# ----------------------------------------------------------------------
# Domain -> Model
# ----------------------------------------------------------------------


def inspection_to_model(inspection: Inspection) -> InspectionModel:
    """Build a fully-populated ORM model from a domain aggregate.

    Children are mapped too: callers use this on save when the aggregate is new.
    """
    return InspectionModel(
        id=inspection.id,
        title=inspection.title,
        location=inspection.location,
        status=inspection.status.value,
        version=inspection.version.value,
        created_by=inspection.created_by,
        created_at=inspection.created_at,
        updated_at=inspection.updated_at,
        observations=[observation_to_model(o) for o in inspection.observations],
        evidences=[evidence_to_model(e) for e in inspection.evidences],
    )


def observation_to_model(observation: Observation) -> ObservationModel:
    return ObservationModel(
        id=observation.id,
        inspection_id=observation.inspection_id,
        title=observation.title,
        notes=observation.notes,
        version=observation.version.value,
        created_at=observation.created_at,
        updated_at=observation.updated_at,
    )


def evidence_to_model(evidence: Evidence) -> EvidenceModel:
    return EvidenceModel(
        id=evidence.id,
        inspection_id=evidence.inspection_id,
        observation_id=evidence.observation_id,
        storage_key=evidence.storage_key,
        mime_type=evidence.mime_type,
        file_size_bytes=evidence.file_size_bytes,
        sha256=evidence.sha256,
        uploaded_at=evidence.uploaded_at,
    )


# ----------------------------------------------------------------------
# Model -> Domain
# ----------------------------------------------------------------------


def inspection_to_domain(model: InspectionModel) -> Inspection:
    """Rebuild the domain aggregate from a fully-loaded ORM model.

    The model must come with ``observations`` and ``evidences`` already loaded
    (the repository uses ``selectin`` eager loading to guarantee that).
    """
    return Inspection(
        id=InspectionId(model.id),
        title=model.title,
        location=model.location,
        status=InspectionStatus(model.status),
        version=Version(model.version),
        created_by=UserId(model.created_by),
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
        observations=[observation_to_domain(o) for o in model.observations],
        evidences=[evidence_to_domain(e) for e in model.evidences],
    )


def observation_to_domain(model: ObservationModel) -> Observation:
    return Observation(
        id=ObservationId(model.id),
        inspection_id=InspectionId(model.inspection_id),
        title=model.title,
        notes=model.notes,
        version=Version(model.version),
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
    )


def evidence_to_domain(model: EvidenceModel) -> Evidence:
    return Evidence(
        id=EvidenceId(model.id),
        inspection_id=InspectionId(model.inspection_id),
        observation_id=(
            ObservationId(model.observation_id) if model.observation_id is not None else None
        ),
        storage_key=model.storage_key,
        mime_type=model.mime_type,
        file_size_bytes=model.file_size_bytes,
        sha256=model.sha256,
        uploaded_at=_as_utc(model.uploaded_at),
    )