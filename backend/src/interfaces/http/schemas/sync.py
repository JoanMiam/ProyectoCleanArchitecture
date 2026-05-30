from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.application.dto.sync_dto import (
    AppliedChangeDTO,
    ChangeSetDTO,
    ConflictResultDTO,
    RejectedChangeDTO,
    SyncBatchDTO,
    SyncResponseDTO,
)


class ChangeSetRequest(BaseModel):
    id: UUID
    entity_id: UUID
    entity_type: str
    operation: str
    base_version: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    def to_dto(self) -> ChangeSetDTO:
        return ChangeSetDTO(
            id=self.id,
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            operation=self.operation,
            base_version=self.base_version,
            payload=self.payload,
            created_at=self.created_at,
        )


class SyncBatchRequest(BaseModel):
    batch_id: UUID
    client_id: str = Field(min_length=1, max_length=100)
    changes: list[ChangeSetRequest] = Field(min_length=1)

    def to_dto(self) -> SyncBatchDTO:
        return SyncBatchDTO(
            batch_id=self.batch_id,
            client_id=self.client_id,
            changes=[change.to_dto() for change in self.changes],
        )


class AppliedChangeResponse(BaseModel):
    change_id: UUID
    new_version: int

    @classmethod
    def from_dto(cls, dto: AppliedChangeDTO) -> "AppliedChangeResponse":
        return cls(change_id=dto.change_id, new_version=dto.new_version)


class ConflictResultResponse(BaseModel):
    change_id: UUID
    entity_id: UUID
    entity_type: str
    server_version: int
    client_version: int
    server_state: dict[str, Any]
    reason: str

    @classmethod
    def from_dto(cls, dto: ConflictResultDTO) -> "ConflictResultResponse":
        return cls(
            change_id=dto.change_id,
            entity_id=dto.entity_id,
            entity_type=dto.entity_type,
            server_version=dto.server_version,
            client_version=dto.client_version,
            server_state=dto.server_state,
            reason=dto.reason,
        )


class RejectedChangeResponse(BaseModel):
    change_id: UUID
    reason: str
    conflict: ConflictResultResponse | None = None

    @classmethod
    def from_dto(cls, dto: RejectedChangeDTO) -> "RejectedChangeResponse":
        return cls(
            change_id=dto.change_id,
            reason=dto.reason,
            conflict=(
                ConflictResultResponse.from_dto(dto.conflict)
                if dto.conflict is not None
                else None
            ),
        )


class SyncResponse(BaseModel):
    batch_id: UUID
    status: str
    applied_changes: list[AppliedChangeResponse]
    rejected_changes: list[RejectedChangeResponse]
    server_delta: dict[str, Any]

    @classmethod
    def from_dto(cls, dto: SyncResponseDTO) -> "SyncResponse":
        return cls(
            batch_id=dto.batch_id,
            status=dto.status,
            applied_changes=[
                AppliedChangeResponse.from_dto(change) for change in dto.applied_changes
            ],
            rejected_changes=[
                RejectedChangeResponse.from_dto(change) for change in dto.rejected_changes
            ],
            server_delta=dto.server_delta,
        )
