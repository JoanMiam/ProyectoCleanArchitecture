from __future__ import annotations

import hashlib
import re
from contextlib import suppress
from pathlib import PurePath
from uuid import uuid4

from src.application.dto.attach_evidence_dto import (
    AttachEvidenceInput,
    AttachEvidenceOutput,
)
from src.application.ports.clock import Clock
from src.application.ports.file_storage_gateway import FileStorageGateway
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.value_objects.ids import EvidenceId, InspectionId, ObservationId, UserId

_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class InvalidEvidenceError(ValueError):
    """Raised when uploaded evidence metadata is not usable."""


class AttachEvidence:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        storage: FileStorageGateway,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._storage = storage

    async def execute(self, cmd: AttachEvidenceInput) -> AttachEvidenceOutput:
        self._validate(cmd)
        inspection_id = InspectionId(cmd.inspection_id)
        evidence_id = EvidenceId(uuid4())
        storage_key = self._build_storage_key(
            inspection_id=inspection_id,
            evidence_id=evidence_id,
            filename=cmd.filename,
        )
        sha256 = hashlib.sha256(cmd.content).hexdigest()
        uploaded_key: str | None = None
        committed = False

        try:
            async with self._uow:
                inspection = await self._uow.inspections.get(inspection_id)
                evidence = inspection.attach_evidence(
                    evidence_id=evidence_id,
                    storage_key=storage_key,
                    mime_type=cmd.mime_type,
                    file_size_bytes=len(cmd.content),
                    sha256=sha256,
                    actor=UserId(cmd.user_id),
                    now=self._clock.now(),
                    observation_id=(
                        ObservationId(cmd.observation_id)
                        if cmd.observation_id is not None
                        else None
                    ),
                )
                uploaded_key = storage_key
                await self._storage.put(
                    key=storage_key,
                    content=cmd.content,
                    content_type=cmd.mime_type,
                )
                await self._uow.inspections.save(inspection)
                await self._uow.commit()
                committed = True
        except Exception:
            if uploaded_key is not None and not committed:
                with suppress(Exception):
                    await self._storage.delete(uploaded_key)
            raise

        return AttachEvidenceOutput(
            inspection_id=evidence.inspection_id,
            evidence_id=evidence.id,
            observation_id=evidence.observation_id,
            storage_key=evidence.storage_key,
            mime_type=evidence.mime_type,
            file_size_bytes=evidence.file_size_bytes,
            sha256=evidence.sha256,
            version=inspection.version.value,
        )

    @staticmethod
    def _validate(cmd: AttachEvidenceInput) -> None:
        if len(cmd.content) == 0:
            raise InvalidEvidenceError("Evidence file must not be empty.")
        if not cmd.mime_type.strip():
            raise InvalidEvidenceError("Evidence mime type is required.")

    @classmethod
    def _build_storage_key(
        cls, inspection_id: InspectionId, evidence_id: EvidenceId, filename: str
    ) -> str:
        safe_filename = cls._sanitize_filename(filename)
        return f"inspections/{inspection_id}/evidences/{evidence_id}/{safe_filename}"

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        basename = PurePath(filename).name.strip()
        if not basename:
            return "evidence"
        safe = _SAFE_FILENAME_PATTERN.sub("-", basename).strip(".-")
        return safe or "evidence"
