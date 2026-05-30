from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from src.application.dto.sync_dto import (
    AppliedChangeDTO,
    ConflictResultDTO,
    RejectedChangeDTO,
    SyncBatchDTO,
    SyncResponseDTO,
)
from src.application.ports.changeset_repository import ChangeSetRepository
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.value_objects.ids import InspectionId


class ApplyChangesBatch:
    def __init__(self, uow: UnitOfWork, changeset_repo: ChangeSetRepository) -> None:
        self.uow = uow
        self.changeset_repo = changeset_repo

    async def execute(self, batch: SyncBatchDTO) -> SyncResponseDTO:
        applied_changes: list[AppliedChangeDTO] = []
        rejected_changes: list[RejectedChangeDTO] = []
        server_delta: dict[str, Any] = {"inspections": []}
        any_conflict = False

        async with self.uow:
            for change in batch.changes:
                # 1. Idempotencia
                if await self.changeset_repo.has_been_applied(change.id):
                    existing = await self.changeset_repo.get_applied(change.id)
                    if existing:
                        applied_changes.append(existing)
                    continue

                # 2. Procesar Cambio
                if change.entity_type == "inspection":
                    inspection_id = InspectionId(change.entity_id)
                    inspection = await self.uow.inspections.get(inspection_id)

                    # Validar Versión
                    client_ver = inspection.version.__class__(change.base_version)
                    if not inspection.version.is_base_for(client_ver):
                        any_conflict = True
                        conflict = ConflictResultDTO(
                            change_id=change.id,
                            entity_id=change.entity_id,
                            entity_type="inspection",
                            server_version=inspection.version.value,
                            client_version=change.base_version,
                            server_state=asdict(inspection)
                        )
                        rejected_changes.append(
                            RejectedChangeDTO(change.id, "version_mismatch", conflict)
                        )
                        continue

                    # Aplicar Mutación
                    if change.operation == "update":
                        inspection.edit(
                            title=change.payload.get("title"),
                            location=change.payload.get("location"),
                            now=datetime.now(UTC).replace(tzinfo=None)
                        )
                    
                    await self.uow.inspections.save(inspection)
                    
                    applied = AppliedChangeDTO(change.id, inspection.version.value)
                    await self.changeset_repo.record_applied(applied)
                    applied_changes.append(applied)
                    server_delta["inspections"].append(asdict(inspection))

            await self.uow.commit()

        status = "success"
        if any_conflict:
            status = "conflict" if not applied_changes else "partial_success"
        
        return SyncResponseDTO(
            batch_id=batch.batch_id,
            status=status,
            applied_changes=applied_changes,
            rejected_changes=rejected_changes,
            server_delta=server_delta
        )
