from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.application.dto.get_inspection_dto import GetInspectionOutput
from src.application.dto.list_inspections_dto import ListInspectionsOutput


class CreateInspectionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    location: str = Field(min_length=1, max_length=500)


class EditInspectionRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    location: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def require_editable_field(self) -> Self:
        if self.title is None and self.location is None:
            raise ValueError("At least one editable field is required.")
        return self


class InspectionMutationResponse(BaseModel):
    inspection_id: UUID
    version: int
    status: str


class ObservationResponse(BaseModel):
    observation_id: UUID
    title: str
    notes: str
    version: int


class InspectionDetailResponse(BaseModel):
    inspection_id: UUID
    title: str
    location: str
    status: str
    version: int
    created_by: UUID
    observations: list[ObservationResponse]
    evidence_count: int

    @classmethod
    def from_output(cls, output: GetInspectionOutput) -> "InspectionDetailResponse":
        return cls(
            inspection_id=output.inspection_id,
            title=output.title,
            location=output.location,
            status=output.status,
            version=output.version,
            created_by=output.created_by,
            observations=[
                ObservationResponse(
                    observation_id=obs.observation_id,
                    title=obs.title,
                    notes=obs.notes,
                    version=obs.version,
                )
                for obs in output.observations
            ],
            evidence_count=output.evidence_count,
        )


class InspectionSummaryResponse(BaseModel):
    inspection_id: UUID
    title: str
    location: str
    status: str
    version: int


class InspectionListResponse(BaseModel):
    items: list[InspectionSummaryResponse]
    count: int

    @classmethod
    def from_output(cls, output: ListInspectionsOutput) -> "InspectionListResponse":
        return cls(
            items=[
                InspectionSummaryResponse(
                    inspection_id=item.inspection_id,
                    title=item.title,
                    location=item.location,
                    status=item.status,
                    version=item.version,
                )
                for item in output.items
            ],
            count=output.count,
        )
