from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime


@dataclass(frozen=True)
class InspectionCreated(DomainEvent):
    inspection_id: UUID
    created_by: UUID


@dataclass(frozen=True)
class InspectionSubmitted(DomainEvent):
    inspection_id: UUID
    submitted_by: UUID


@dataclass(frozen=True)
class InspectionClosed(DomainEvent):
    inspection_id: UUID
    closed_by: UUID


@dataclass(frozen=True)
class ObservationAdded(DomainEvent):
    inspection_id: UUID
    observation_id: UUID
    added_by: UUID


@dataclass(frozen=True)
class ObservationEdited(DomainEvent):
    inspection_id: UUID
    observation_id: UUID
    edited_by: UUID


@dataclass(frozen=True)
class ObservationRemoved(DomainEvent):
    inspection_id: UUID
    observation_id: UUID
    removed_by: UUID


@dataclass(frozen=True)
class EvidenceAttached(DomainEvent):
    inspection_id: UUID
    evidence_id: UUID
    attached_by: UUID
