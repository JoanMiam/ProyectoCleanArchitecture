from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ChangeSetDTO:
    """Representa un cambio individual originado en el cliente."""
    id: UUID
    entity_id: UUID
    entity_type: str  # e.g., "inspection", "observation"
    operation: str    # "create", "update", "delete"
    base_version: int
    payload: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class SyncBatchDTO:
    """Lote de cambios enviado por el cliente."""
    batch_id: UUID
    client_id: str
    changes: list[ChangeSetDTO]


@dataclass(frozen=True)
class AppliedChangeDTO:
    """Información de un cambio aceptado y aplicado."""
    change_id: UUID
    new_version: int


@dataclass(frozen=True)
class ConflictResultDTO:
    """Detalle de un conflicto detectado por mismatch de versión."""
    change_id: UUID
    entity_id: UUID
    entity_type: str
    server_version: int
    client_version: int
    server_state: dict[str, Any]
    reason: str = "version_mismatch"


@dataclass(frozen=True)
class RejectedChangeDTO:
    """Información de un cambio rechazado (por error o conflicto)."""
    change_id: UUID
    reason: str
    conflict: ConflictResultDTO | None = None


@dataclass(frozen=True)
class SyncResponseDTO:
    """Respuesta completa del servidor tras procesar un SyncBatch."""
    batch_id: UUID
    status: str  # "success", "partial_success", "conflict"
    applied_changes: list[AppliedChangeDTO] = field(default_factory=list)
    rejected_changes: list[RejectedChangeDTO] = field(default_factory=list)
    server_delta: dict[str, Any] = field(default_factory=dict)
