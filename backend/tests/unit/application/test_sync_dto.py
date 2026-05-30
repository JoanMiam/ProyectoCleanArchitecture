from datetime import datetime
from uuid import uuid4

from src.application.dto.sync_dto import (
    AppliedChangeDTO,
    ChangeSetDTO,
    ConflictResultDTO,
    SyncBatchDTO,
    SyncResponseDTO,
)


def test_create_change_set_dto():
    change_id = uuid4()
    entity_id = uuid4()
    now = datetime.utcnow()
    
    dto = ChangeSetDTO(
        id=change_id,
        entity_id=entity_id,
        entity_type="inspection",
        operation="update",
        base_version=1,
        payload={"notes": "updated"},
        created_at=now
    )
    
    assert dto.id == change_id
    assert dto.base_version == 1
    assert dto.payload["notes"] == "updated"

def test_create_sync_batch_dto():
    batch_id = uuid4()
    change_dto = ChangeSetDTO(
        id=uuid4(),
        entity_id=uuid4(),
        entity_type="inspection",
        operation="create",
        base_version=0,
        payload={},
        created_at=datetime.utcnow()
    )
    
    dto = SyncBatchDTO(
        batch_id=batch_id,
        client_id="client-123",
        changes=[change_dto]
    )
    
    assert dto.batch_id == batch_id
    assert len(dto.changes) == 1

def test_create_sync_response_dto():
    batch_id = uuid4()
    change_id = uuid4()
    
    applied = AppliedChangeDTO(change_id=change_id, new_version=2)
    
    dto = SyncResponseDTO(
        batch_id=batch_id,
        status="success",
        applied_changes=[applied]
    )
    
    assert dto.batch_id == batch_id
    assert dto.status == "success"
    assert dto.applied_changes[0].new_version == 2

def test_create_conflict_result_dto():
    change_id = uuid4()
    entity_id = uuid4()
    
    dto = ConflictResultDTO(
        change_id=change_id,
        entity_id=entity_id,
        entity_type="inspection",
        server_version=5,
        client_version=3,
        server_state={"status": "completed"}
    )
    
    assert dto.server_version == 5
    assert dto.reason == "version_mismatch"
