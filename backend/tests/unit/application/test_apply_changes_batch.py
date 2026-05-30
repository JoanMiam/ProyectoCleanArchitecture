from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.dto.sync_dto import ChangeSetDTO, SyncBatchDTO
from src.domain.entities.inspection import Inspection
from src.domain.value_objects.ids import InspectionId, UserId
from src.domain.value_objects.version import Version
from tests.unit.application.fakes import FakeUnitOfWork

# Nota: El caso de uso aún no existe, lo importaremos después de definirlo
# Para TDD, el test fallará inicialmente por ImportError o NameError

@pytest.fixture
def uow():
    return FakeUnitOfWork()

@pytest.fixture
def existing_inspection(uow):
    inspection = Inspection.create(
        id=InspectionId(uuid4()),
        title="Test Inspection",
        location="Test Location",
        created_by=UserId(uuid4()),
        now=datetime.now(UTC)
    )
    # Forzar versión 1 para pruebas de conflicto
    inspection.version = Version(1)
    uow.inspections.inspections[inspection.id] = inspection
    return inspection

@pytest.mark.asyncio
async def test_apply_changes_success(uow, existing_inspection):
    from src.application.use_cases.apply_changes_batch import ApplyChangesBatch
    
    use_case = ApplyChangesBatch(uow, uow.changesets)
    
    change = ChangeSetDTO(
        id=uuid4(),
        entity_id=existing_inspection.id,
        entity_type="inspection",
        operation="update",
        base_version=1,
        payload={"title": "New Title"},
        created_at=datetime.now(UTC)
    )
    
    batch = SyncBatchDTO(
        batch_id=uuid4(),
        client_id="client-1",
        changes=[change]
    )
    
    response = await use_case.execute(batch)
    
    assert response.status == "success"
    assert len(response.applied_changes) == 1
    assert response.applied_changes[0].change_id == change.id
    
    updated = await uow.inspections.get(existing_inspection.id)
    assert updated.title == "New Title"
    assert updated.version == Version(2)

@pytest.mark.asyncio
async def test_apply_changes_idempotency(uow, existing_inspection):
    from src.application.use_cases.apply_changes_batch import ApplyChangesBatch
    
    use_case = ApplyChangesBatch(uow, uow.changesets)
    
    change = ChangeSetDTO(
        id=uuid4(),
        entity_id=existing_inspection.id,
        entity_type="inspection",
        operation="update",
        base_version=1,
        payload={"title": "First Edit"},
        created_at=datetime.now(UTC)
    )
    
    batch = SyncBatchDTO(batch_id=uuid4(), client_id="c1", changes=[change])
    
    # Primera vez
    await use_case.execute(batch)
    
    # Segunda vez (mismo change_id)
    response = await use_case.execute(batch)
    
    assert response.status == "success"
    assert len(response.applied_changes) == 1
    assert response.server_delta["inspections"][0]["title"] == "First Edit"
    
    updated = await uow.inspections.get(existing_inspection.id)
    assert updated.version == Version(2) # No debe subir a 3

@pytest.mark.asyncio
async def test_apply_changes_conflict(uow, existing_inspection):
    from src.application.use_cases.apply_changes_batch import ApplyChangesBatch
    
    use_case = ApplyChangesBatch(uow, uow.changesets)
    
    change = ChangeSetDTO(
        id=uuid4(),
        entity_id=existing_inspection.id,
        entity_type="inspection",
        operation="update",
        base_version=0, # Debería ser 1
        payload={"title": "Conflicting Title"},
        created_at=datetime.now(UTC)
    )
    
    batch = SyncBatchDTO(batch_id=uuid4(), client_id="c1", changes=[change])
    
    response = await use_case.execute(batch)
    
    assert response.status == "conflict"
    assert len(response.rejected_changes) == 1
    assert response.rejected_changes[0].conflict.reason == "version_mismatch"
    assert response.rejected_changes[0].conflict.server_version == 1
    assert "_events" not in response.rejected_changes[0].conflict.server_state


@pytest.mark.asyncio
async def test_apply_changes_rejects_unsupported_entity_type(uow):
    from src.application.use_cases.apply_changes_batch import ApplyChangesBatch

    use_case = ApplyChangesBatch(uow, uow.changesets)

    change = ChangeSetDTO(
        id=uuid4(),
        entity_id=uuid4(),
        entity_type="observation",
        operation="update",
        base_version=0,
        payload={"title": "Ignored"},
        created_at=datetime.now(UTC)
    )

    response = await use_case.execute(
        SyncBatchDTO(batch_id=uuid4(), client_id="c1", changes=[change])
    )

    assert response.status != "success"
    assert response.applied_changes == []
    assert response.rejected_changes[0].reason == "unsupported_entity_type"


@pytest.mark.asyncio
async def test_apply_changes_rejects_unsupported_operation(uow, existing_inspection):
    from src.application.use_cases.apply_changes_batch import ApplyChangesBatch

    use_case = ApplyChangesBatch(uow, uow.changesets)

    change = ChangeSetDTO(
        id=uuid4(),
        entity_id=existing_inspection.id,
        entity_type="inspection",
        operation="delete",
        base_version=1,
        payload={},
        created_at=datetime.now(UTC)
    )

    response = await use_case.execute(
        SyncBatchDTO(batch_id=uuid4(), client_id="c1", changes=[change])
    )

    updated = await uow.inspections.get(existing_inspection.id)
    assert response.status != "success"
    assert response.applied_changes == []
    assert response.rejected_changes[0].reason == "unsupported_operation"
    assert updated.version == Version(1)


@pytest.mark.asyncio
async def test_apply_changes_rejects_empty_update_payload(uow, existing_inspection):
    from src.application.use_cases.apply_changes_batch import ApplyChangesBatch

    use_case = ApplyChangesBatch(uow, uow.changesets)

    change = ChangeSetDTO(
        id=uuid4(),
        entity_id=existing_inspection.id,
        entity_type="inspection",
        operation="update",
        base_version=1,
        payload={},
        created_at=datetime.now(UTC)
    )

    response = await use_case.execute(
        SyncBatchDTO(batch_id=uuid4(), client_id="c1", changes=[change])
    )

    updated = await uow.inspections.get(existing_inspection.id)
    assert response.status != "success"
    assert response.applied_changes == []
    assert response.rejected_changes[0].reason == "empty_update_payload"
    assert updated.version == Version(1)


@pytest.mark.asyncio
async def test_apply_changes_rejects_invalid_payload(uow, existing_inspection):
    from src.application.use_cases.apply_changes_batch import ApplyChangesBatch

    use_case = ApplyChangesBatch(uow, uow.changesets)

    change = ChangeSetDTO(
        id=uuid4(),
        entity_id=existing_inspection.id,
        entity_type="inspection",
        operation="update",
        base_version=1,
        payload={"title": 123},
        created_at=datetime.now(UTC)
    )

    response = await use_case.execute(
        SyncBatchDTO(batch_id=uuid4(), client_id="c1", changes=[change])
    )

    updated = await uow.inspections.get(existing_inspection.id)
    assert response.status != "success"
    assert response.applied_changes == []
    assert response.rejected_changes[0].reason == "invalid_payload"
    assert updated.version == Version(1)


@pytest.mark.asyncio
async def test_apply_changes_rejects_missing_entity(uow):
    from src.application.use_cases.apply_changes_batch import ApplyChangesBatch

    use_case = ApplyChangesBatch(uow, uow.changesets)

    change = ChangeSetDTO(
        id=uuid4(),
        entity_id=uuid4(),
        entity_type="inspection",
        operation="update",
        base_version=0,
        payload={"title": "Missing"},
        created_at=datetime.now(UTC)
    )

    response = await use_case.execute(
        SyncBatchDTO(batch_id=uuid4(), client_id="c1", changes=[change])
    )

    assert response.status != "success"
    assert response.applied_changes == []
    assert response.rejected_changes[0].reason == "entity_not_found"
