"""Unit tests for GetAuditTrail use case."""
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.use_cases.get_audit_trail import GetAuditTrail, GetAuditTrailInput
from src.domain.entities.inspection import Inspection
from src.domain.value_objects.ids import InspectionId, UserId
from tests.unit.conftest import FakeAuditRepository


def _make_inspection(user_id: None = None) -> Inspection:
    now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)
    uid = user_id or UserId(uuid4())
    return Inspection.create(
        id=InspectionId(uuid4()),
        title="Site Check",
        location="Warehouse A",
        created_by=uid,
        now=now,
    )


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetAuditTrail:
    @pytest.fixture
    def audit_repo(self) -> FakeAuditRepository:
        return FakeAuditRepository()

    @pytest.fixture
    def use_case(self, audit_repo: FakeAuditRepository) -> GetAuditTrail:
        return GetAuditTrail(audit_repo=audit_repo)

    async def test_empty_trail_returns_empty_list(self, use_case: GetAuditTrail) -> None:
        output = await use_case.execute(GetAuditTrailInput(inspection_id=uuid4()))
        assert output.entries == []

    async def test_returns_entry_after_append(
        self,
        audit_repo: FakeAuditRepository,
        use_case: GetAuditTrail,
    ) -> None:
        inspection = _make_inspection()
        events = inspection.collect_events()
        await audit_repo.append_many(events)

        output = await use_case.execute(GetAuditTrailInput(inspection_id=inspection.id))

        assert len(output.entries) == 1
        entry = output.entries[0]
        assert entry.event_type == "InspectionCreated"
        assert entry.aggregate_id == inspection.id
        assert entry.aggregate_type == "Inspection"

    async def test_filters_by_inspection_id(
        self,
        audit_repo: FakeAuditRepository,
        use_case: GetAuditTrail,
    ) -> None:
        insp_a = _make_inspection()
        insp_b = _make_inspection()

        await audit_repo.append_many(insp_a.collect_events())
        await audit_repo.append_many(insp_b.collect_events())

        output = await use_case.execute(GetAuditTrailInput(inspection_id=insp_a.id))

        assert len(output.entries) == 1
        assert output.entries[0].aggregate_id == insp_a.id

    async def test_returns_multiple_events_in_order(
        self,
        audit_repo: FakeAuditRepository,
        use_case: GetAuditTrail,
    ) -> None:
        actor = UserId(uuid4())
        inspection = _make_inspection(user_id=actor)
        _ = inspection.collect_events()  # consume creation event

        now = datetime(2026, 1, 15, 10, 5, 0, tzinfo=UTC)
        inspection.add_observation(title="Crack", notes="East wall", actor=actor, now=now)
        await audit_repo.append_many(inspection.collect_events())

        inspection.submit(actor=actor, now=datetime(2026, 1, 15, 10, 10, 0, tzinfo=UTC))
        await audit_repo.append_many(inspection.collect_events())

        output = await use_case.execute(GetAuditTrailInput(inspection_id=inspection.id))

        assert len(output.entries) == 2
        assert output.entries[0].event_type == "ObservationAdded"
        assert output.entries[1].event_type == "InspectionSubmitted"

    async def test_actor_id_extracted_correctly(
        self,
        audit_repo: FakeAuditRepository,
        use_case: GetAuditTrail,
    ) -> None:
        actor = UserId(uuid4())
        inspection = Inspection.create(
            id=InspectionId(uuid4()),
            title="T",
            location="L",
            created_by=actor,
            now=datetime(2026, 1, 15, tzinfo=UTC),
        )
        await audit_repo.append_many(inspection.collect_events())

        output = await use_case.execute(GetAuditTrailInput(inspection_id=inspection.id))

        assert output.entries[0].actor_id == actor
