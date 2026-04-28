"""TDD tests for Inspection aggregate root."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from src.domain.entities.inspection import Inspection
from src.domain.exceptions import InvalidStateError, ObservationNotFound
from src.domain.value_objects.ids import EvidenceId, InspectionId, UserId
from src.domain.value_objects.inspection_status import InspectionStatus
from src.domain.value_objects.version import Version

NOW = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
ACTOR = UserId(UUID("00000000-0000-0000-0000-000000000001"))


def make_inspection(**kwargs: object) -> Inspection:
    defaults = dict(
        id=InspectionId(uuid4()),
        created_by=ACTOR,
        now=NOW,
    )
    defaults.update(kwargs)
    return Inspection.create(
        id=defaults["id"],  # type: ignore[arg-type]
        title=defaults.get("title", "Test Inspection"),  # type: ignore[arg-type]
        location=defaults.get("location", "Warehouse A"),  # type: ignore[arg-type]
        created_by=defaults["created_by"],  # type: ignore[arg-type]
        now=defaults["now"],  # type: ignore[arg-type]
    )


class TestInspectionCreation:
    def test_new_inspection_has_draft_status(self) -> None:
        inspection = make_inspection()
        assert inspection.status == InspectionStatus.DRAFT

    def test_new_inspection_starts_at_version_zero(self) -> None:
        inspection = make_inspection()
        assert inspection.version == Version(0)

    def test_new_inspection_has_no_observations(self) -> None:
        inspection = make_inspection()
        assert inspection.observations == []

    def test_new_inspection_has_no_evidences(self) -> None:
        inspection = make_inspection()
        assert inspection.evidences == []

    def test_create_emits_inspection_created_event(self) -> None:
        inspection = make_inspection()
        events = inspection.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "InspectionCreated"

    def test_collect_events_clears_them(self) -> None:
        inspection = make_inspection()
        inspection.collect_events()
        assert inspection.collect_events() == []


class TestInspectionEditing:
    def test_edit_title_on_draft_succeeds(self) -> None:
        inspection = make_inspection(title="Old Title")
        inspection.edit(title="New Title", now=NOW)
        assert inspection.title == "New Title"

    def test_edit_increments_version(self) -> None:
        inspection = make_inspection()
        inspection.edit(title="Updated", now=NOW)
        assert inspection.version == Version(1)

    def test_multiple_edits_increment_version_each_time(self) -> None:
        inspection = make_inspection()
        inspection.edit(title="Edit 1", now=NOW)
        inspection.edit(location="New Location", now=NOW)
        assert inspection.version == Version(2)

    def test_edit_closed_inspection_raises(self) -> None:
        inspection = make_inspection()
        inspection.submit(actor=ACTOR, now=NOW)
        inspection.close(actor=ACTOR, now=NOW)
        with pytest.raises(InvalidStateError):
            inspection.edit(title="Should fail", now=NOW)

    def test_edit_submitted_inspection_raises(self) -> None:
        inspection = make_inspection()
        inspection.submit(actor=ACTOR, now=NOW)
        with pytest.raises(InvalidStateError):
            inspection.edit(title="Should fail", now=NOW)


class TestObservations:
    def test_add_observation_to_draft_succeeds(self) -> None:
        inspection = make_inspection()
        obs = inspection.add_observation(title="Crack in wall", notes="5cm crack", actor=ACTOR, now=NOW)
        assert len(inspection.observations) == 1
        assert obs.title == "Crack in wall"

    def test_add_observation_increments_inspection_version(self) -> None:
        inspection = make_inspection()
        inspection.add_observation(title="Obs", notes="", actor=ACTOR, now=NOW)
        assert inspection.version == Version(1)

    def test_add_observation_to_closed_raises(self) -> None:
        inspection = make_inspection()
        inspection.submit(actor=ACTOR, now=NOW)
        inspection.close(actor=ACTOR, now=NOW)
        with pytest.raises(InvalidStateError):
            inspection.add_observation(title="Should fail", notes="", actor=ACTOR, now=NOW)

    def test_edit_observation_updates_notes(self) -> None:
        inspection = make_inspection()
        obs = inspection.add_observation(title="Obs", notes="old notes", actor=ACTOR, now=NOW)
        inspection.edit_observation(obs.id, notes="new notes", actor=ACTOR, now=NOW)
        assert inspection.observations[0].notes == "new notes"

    def test_edit_nonexistent_observation_raises(self) -> None:
        from src.domain.value_objects.ids import ObservationId
        inspection = make_inspection()
        with pytest.raises(ObservationNotFound):
            inspection.edit_observation(ObservationId(uuid4()), notes="x")

    def test_remove_observation_removes_it(self) -> None:
        inspection = make_inspection()
        obs = inspection.add_observation(title="Obs", notes="", actor=ACTOR, now=NOW)
        inspection.remove_observation(obs.id, actor=ACTOR, now=NOW)
        assert inspection.observations == []


class TestStatusTransitions:
    def test_submit_draft_inspection_succeeds(self) -> None:
        inspection = make_inspection()
        inspection.submit(actor=ACTOR, now=NOW)
        assert inspection.status == InspectionStatus.SUBMITTED

    def test_submit_increments_version(self) -> None:
        inspection = make_inspection()
        inspection.submit(actor=ACTOR, now=NOW)
        assert inspection.version == Version(1)

    def test_close_submitted_inspection_succeeds(self) -> None:
        inspection = make_inspection()
        inspection.submit(actor=ACTOR, now=NOW)
        inspection.close(actor=ACTOR, now=NOW)
        assert inspection.status == InspectionStatus.CLOSED

    def test_close_draft_inspection_raises(self) -> None:
        inspection = make_inspection()
        with pytest.raises(InvalidStateError):
            inspection.close(actor=ACTOR, now=NOW)

    def test_submit_closed_inspection_raises(self) -> None:
        inspection = make_inspection()
        inspection.submit(actor=ACTOR, now=NOW)
        inspection.close(actor=ACTOR, now=NOW)
        with pytest.raises(InvalidStateError):
            inspection.submit(actor=ACTOR, now=NOW)


class TestEvidences:
    def test_attach_evidence_stores_reference(self) -> None:
        inspection = make_inspection()
        evidence = inspection.attach_evidence(
            evidence_id=EvidenceId(uuid4()),
            storage_key="evidences/photo.jpg",
            mime_type="image/jpeg",
            file_size_bytes=1024,
            sha256="abc123",
            actor=ACTOR,
            now=NOW,
        )
        assert len(inspection.evidences) == 1
        assert evidence.storage_key == "evidences/photo.jpg"

    def test_attach_evidence_increments_version(self) -> None:
        inspection = make_inspection()
        inspection.attach_evidence(
            evidence_id=EvidenceId(uuid4()),
            storage_key="key",
            mime_type="image/png",
            file_size_bytes=512,
            sha256="hash",
            actor=ACTOR,
            now=NOW,
        )
        assert inspection.version == Version(1)

    def test_attach_evidence_to_closed_inspection_raises(self) -> None:
        inspection = make_inspection()
        inspection.submit(actor=ACTOR, now=NOW)
        inspection.close(actor=ACTOR, now=NOW)
        with pytest.raises(InvalidStateError):
            inspection.attach_evidence(
                evidence_id=EvidenceId(uuid4()),
                storage_key="key",
                mime_type="image/png",
                file_size_bytes=512,
                sha256="hash",
                actor=ACTOR,
                now=NOW,
            )
