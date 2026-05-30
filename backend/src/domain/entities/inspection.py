from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.domain.entities.evidence import Evidence
from src.domain.entities.observation import Observation
from src.domain.events import (
    DomainEvent,
    EvidenceAttached,
    InspectionClosed,
    InspectionCreated,
    InspectionSubmitted,
    ObservationAdded,
    ObservationEdited,
    ObservationRemoved,
)
from src.domain.exceptions import InvalidStateError, ObservationNotFoundError
from src.domain.value_objects.ids import (
    EvidenceId,
    InspectionId,
    ObservationId,
    UserId,
)
from src.domain.value_objects.inspection_status import InspectionStatus
from src.domain.value_objects.version import Version


@dataclass
class Inspection:
    """
    Aggregate root for an inspection.

    Invariants:
    - CLOSED inspections cannot be edited without explicit reopen.
    - Observations and evidences always reference this inspection.
    - Version is monotonically increasing; each mutation increments it.
    - Domain events accumulate in _events and are cleared after persistence.
    """

    id: InspectionId
    title: str
    location: str
    status: InspectionStatus
    version: Version
    created_by: UserId
    created_at: datetime
    updated_at: datetime
    observations: list[Observation] = field(default_factory=list)
    evidences: list[Evidence] = field(default_factory=list)
    _events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        id: InspectionId,
        title: str,
        location: str,
        created_by: UserId,
        now: datetime,
    ) -> Inspection:
        inspection = cls(
            id=id,
            title=title,
            location=location,
            status=InspectionStatus.DRAFT,
            version=Version(0),
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        inspection._events.append(
            InspectionCreated(occurred_at=now, inspection_id=id, created_by=created_by)
        )
        return inspection

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def edit(
        self,
        title: str | None = None,
        location: str | None = None,
        now: datetime | None = None,
    ) -> None:
        self._assert_editable()
        if title is not None:
            self.title = title
        if location is not None:
            self.location = location
        self._bump_version(now)

    def add_observation(self, title: str, notes: str, actor: UserId, now: datetime) -> Observation:
        self._assert_editable()
        obs = Observation(
            id=ObservationId(uuid4()),
            inspection_id=self.id,
            title=title,
            notes=notes,
            version=Version(0),
            created_at=now,
            updated_at=now,
        )
        self.observations.append(obs)
        self._bump_version(now)
        self._events.append(
            ObservationAdded(
                occurred_at=now,
                inspection_id=self.id,
                observation_id=obs.id,
                added_by=actor,
            )
        )
        return obs

    def edit_observation(
        self,
        observation_id: ObservationId,
        title: str | None = None,
        notes: str | None = None,
        actor: UserId | None = None,
        now: datetime | None = None,
    ) -> None:
        self._assert_editable()
        obs = self._get_observation(observation_id)
        obs.edit(title=title, notes=notes)
        self._bump_version(now)
        if actor and now:
            self._events.append(
                ObservationEdited(
                    occurred_at=now,
                    inspection_id=self.id,
                    observation_id=obs.id,
                    edited_by=actor,
                )
            )

    def remove_observation(
            self, observation_id: ObservationId, actor: UserId, now: datetime
    ) -> None:
        self._assert_editable()
        obs = self._get_observation(observation_id)
        self.observations = [o for o in self.observations if o.id != observation_id]
        self._bump_version(now)
        self._events.append(
            ObservationRemoved(
                occurred_at=now,
                inspection_id=self.id,
                observation_id=obs.id,
                removed_by=actor,
            )
        )

    def attach_evidence(
        self,
        evidence_id: EvidenceId,
        storage_key: str,
        mime_type: str,
        file_size_bytes: int,
        sha256: str,
        actor: UserId,
        now: datetime,
        observation_id: ObservationId | None = None,
    ) -> Evidence:
        self._assert_editable()
        if observation_id is not None:
            self._get_observation(observation_id)  # validates it exists
        evidence = Evidence(
            id=evidence_id,
            inspection_id=self.id,
            observation_id=observation_id,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            sha256=sha256,
            uploaded_at=now,
        )
        self.evidences.append(evidence)
        self._bump_version(now)
        self._events.append(
            EvidenceAttached(
                occurred_at=now,
                inspection_id=self.id,
                evidence_id=evidence_id,
                attached_by=actor,
            )
        )
        return evidence

    def submit(self, actor: UserId, now: datetime) -> None:
        if not self.status.can_submit():
            raise InvalidStateError(
                f"Cannot submit inspection with status '{self.status}'. "
                "Must be DRAFT or IN_PROGRESS."
            )
        self.status = InspectionStatus.SUBMITTED
        self._bump_version(now)
        self._events.append(
            InspectionSubmitted(occurred_at=now, inspection_id=self.id, submitted_by=actor)
        )

    def close(self, actor: UserId, now: datetime) -> None:
        if not self.status.can_close():
            raise InvalidStateError(
                f"Cannot close inspection with status '{self.status}'. Must be SUBMITTED."
            )
        self.status = InspectionStatus.CLOSED
        self._bump_version(now)
        self._events.append(
            InspectionClosed(occurred_at=now, inspection_id=self.id, closed_by=actor)
        )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assert_editable(self) -> None:
        if not self.status.is_editable():
            raise InvalidStateError(
                f"Inspection '{self.id}' cannot be edited in status '{self.status}'. "
                "Only DRAFT or IN_PROGRESS inspections are editable."
            )

    def _bump_version(self, now: datetime | None = None) -> None:
        self.version = self.version.increment()
        if now is not None:
            self.updated_at = now

    def _get_observation(self, observation_id: ObservationId) -> Observation:
        for obs in self.observations:
            if obs.id == observation_id:
                return obs
        raise ObservationNotFoundError(
            f"Observation '{observation_id}' not found in inspection '{self.id}'."
        )
