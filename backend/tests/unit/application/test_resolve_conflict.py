from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.dto.sync_dto import ConflictResultDTO
from src.domain.entities.inspection import Inspection
from src.domain.value_objects.ids import InspectionId, UserId
from src.domain.value_objects.version import Version
from tests.unit.application.fakes import FakeUnitOfWork


@pytest.fixture
def uow():
    return FakeUnitOfWork()

@pytest.fixture
def conflict(uow):
    inspection = Inspection.create(
        id=InspectionId(uuid4()),
        title="Server Title",
        location="Server Loc",
        created_by=UserId(uuid4()),
        now=datetime.now(UTC).replace(tzinfo=None)
    )
    inspection.version = Version(5)
    uow.inspections.inspections[inspection.id] = inspection
    
    change_id = uuid4()
    conflict_dto = ConflictResultDTO(
        change_id=change_id,
        entity_id=inspection.id,
        entity_type="inspection",
        server_version=5,
        client_version=3,
        server_state=asdict(inspection)
    )
    uow.conflicts.conflicts[change_id] = conflict_dto
    return conflict_dto

@pytest.mark.asyncio
async def test_resolve_keep_server(uow, conflict):
    from src.application.use_cases.resolve_conflict import ResolveConflict
    
    use_case = ResolveConflict(uow, uow.conflicts)
    await use_case.execute(conflict.change_id, "keep_server")
    
    assert conflict.change_id in uow.conflicts.resolved
    inspection = await uow.inspections.get(conflict.entity_id)
    assert inspection.version == Version(5) # No cambia

@pytest.mark.asyncio
async def test_resolve_keep_client(uow, conflict):
    from src.application.use_cases.resolve_conflict import ResolveConflict
    
    use_case = ResolveConflict(uow, uow.conflicts)
    # Payload que el cliente quería originalmente
    client_payload = {"title": "Client Win Title"}
    
    await use_case.execute(conflict.change_id, "keep_client", client_payload)
    
    inspection = await uow.inspections.get(conflict.entity_id)
    assert inspection.title == "Client Win Title"
    assert inspection.version == Version(6) # Sube versión
    assert conflict.change_id in uow.conflicts.resolved

@pytest.mark.asyncio
async def test_resolve_manual_merge(uow, conflict):
    from src.application.use_cases.resolve_conflict import ResolveConflict
    
    use_case = ResolveConflict(uow, uow.conflicts)
    merged_payload = {"title": "Merged Title", "location": "Merged Loc"}
    
    await use_case.execute(conflict.change_id, "manual_merge", merged_payload)
    
    inspection = await uow.inspections.get(conflict.entity_id)
    assert inspection.title == "Merged Title"
    assert inspection.location == "Merged Loc"
    assert inspection.version == Version(6)
