from datetime import UTC, datetime
from typing import Any

from src.application.dto.sync_dto import (
    AppliedChangeDTO,
    ConflictResultDTO,
    RejectedChangeDTO,
    SyncBatchDTO,
    SyncResponseDTO,
)
from src.application.ports.audit_repository import AuditRepository
from src.application.ports.changeset_repository import ChangeSetRepository
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.entities.inspection import Inspection
from src.domain.exceptions import InspectionNotFoundError
from src.domain.value_objects.ids import InspectionId
from src.domain.value_objects.version import Version

SUPPORTED_ENTITY_TYPE = "inspection"
SUPPORTED_OPERATION = "update"


class ApplyChangesBatch:
    def __init__(
        self,
        uow: UnitOfWork,
        changeset_repo: ChangeSetRepository | None = None,
        audit_repo: AuditRepository | None = None,
    ) -> None:
        self.uow = uow
        self.changeset_repo = changeset_repo
        self.audit_repo = audit_repo

    async def execute(self, batch: SyncBatchDTO) -> SyncResponseDTO:
        applied_changes: list[AppliedChangeDTO] = []
        rejected_changes: list[RejectedChangeDTO] = []
        server_delta: dict[str, Any] = {"inspections": []}
        any_conflict = False
        _auditable: list[Inspection] = []

        async with self.uow:
            changeset_repo = self.changeset_repo or self.uow.changesets
            for change in batch.changes:
                if await changeset_repo.has_been_applied(change.id):
                    existing = await changeset_repo.get_applied(change.id)
                    if existing is not None:
                        applied_changes.append(existing)
                        self._merge_server_delta(server_delta, existing.server_delta)
                    continue

                if change.entity_type != SUPPORTED_ENTITY_TYPE:
                    rejected_changes.append(
                        RejectedChangeDTO(change.id, "unsupported_entity_type")
                    )
                    continue

                if change.operation != SUPPORTED_OPERATION:
                    rejected_changes.append(
                        RejectedChangeDTO(change.id, "unsupported_operation")
                    )
                    continue

                try:
                    title = self._optional_text_payload(change.payload, "title")
                    location = self._optional_text_payload(change.payload, "location")
                except ValueError:
                    rejected_changes.append(RejectedChangeDTO(change.id, "invalid_payload"))
                    continue

                if title is None and location is None:
                    rejected_changes.append(RejectedChangeDTO(change.id, "empty_update_payload"))
                    continue

                try:
                    inspection = await self.uow.inspections.get(
                        InspectionId(change.entity_id)
                    )
                except InspectionNotFoundError:
                    rejected_changes.append(RejectedChangeDTO(change.id, "entity_not_found"))
                    continue

                client_ver = Version(change.base_version)
                if not inspection.version.is_base_for(client_ver):
                    any_conflict = True
                    conflict = ConflictResultDTO(
                        change_id=change.id,
                        entity_id=change.entity_id,
                        entity_type=SUPPORTED_ENTITY_TYPE,
                        server_version=inspection.version.value,
                        client_version=change.base_version,
                        server_state=self._inspection_delta(inspection),
                    )
                    rejected_changes.append(
                        RejectedChangeDTO(change.id, "version_mismatch", conflict)
                    )
                    continue

                inspection.edit(
                    title=title,
                    location=location,
                    now=datetime.now(UTC).replace(tzinfo=None),
                )
                _auditable.append(inspection)
                await self.uow.inspections.save(inspection)

                change_delta = {"inspections": [self._inspection_delta(inspection)]}
                applied = AppliedChangeDTO(
                    change_id=change.id,
                    new_version=inspection.version.value,
                    server_delta=change_delta,
                )
                await changeset_repo.record_applied(applied)
                applied_changes.append(applied)
                self._merge_server_delta(server_delta, change_delta)

            await self.uow.commit()

        if self.audit_repo is not None:
            for insp in _auditable:
                events = insp.collect_events()
                if events:
                    await self.audit_repo.append_many(events)

        return SyncResponseDTO(
            batch_id=batch.batch_id,
            status=self._response_status(applied_changes, rejected_changes, any_conflict),
            applied_changes=applied_changes,
            rejected_changes=rejected_changes,
            server_delta=server_delta,
        )

    @staticmethod
    def _optional_text_payload(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError
        return value

    @staticmethod
    def _inspection_delta(inspection: Inspection) -> dict[str, Any]:
        return {
            "id": str(inspection.id),
            "title": inspection.title,
            "location": inspection.location,
            "status": inspection.status.value,
            "version": inspection.version.value,
            "created_by": str(inspection.created_by),
            "created_at": inspection.created_at.isoformat(),
            "updated_at": inspection.updated_at.isoformat(),
            "observations": [
                {
                    "id": str(observation.id),
                    "inspection_id": str(observation.inspection_id),
                    "title": observation.title,
                    "notes": observation.notes,
                    "version": observation.version.value,
                    "created_at": observation.created_at.isoformat(),
                    "updated_at": observation.updated_at.isoformat(),
                }
                for observation in inspection.observations
            ],
            "evidences": [
                {
                    "id": str(evidence.id),
                    "inspection_id": str(evidence.inspection_id),
                    "observation_id": (
                        str(evidence.observation_id)
                        if evidence.observation_id is not None
                        else None
                    ),
                    "storage_key": evidence.storage_key,
                    "mime_type": evidence.mime_type,
                    "file_size_bytes": evidence.file_size_bytes,
                    "sha256": evidence.sha256,
                    "uploaded_at": evidence.uploaded_at.isoformat(),
                }
                for evidence in inspection.evidences
            ],
        }

    @staticmethod
    def _merge_server_delta(target: dict[str, Any], source: dict[str, Any]) -> None:
        inspections = source.get("inspections", [])
        if not isinstance(inspections, list):
            return
        target.setdefault("inspections", []).extend(inspections)

    @staticmethod
    def _response_status(
        applied_changes: list[AppliedChangeDTO],
        rejected_changes: list[RejectedChangeDTO],
        any_conflict: bool,
    ) -> str:
        if not rejected_changes:
            return "success"
        if any_conflict and not applied_changes:
            return "conflict"
        return "partial_success"
