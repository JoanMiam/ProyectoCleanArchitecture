from enum import StrEnum


class InspectionStatus(StrEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    CLOSED = "closed"

    def is_editable(self) -> bool:
        return self in (InspectionStatus.DRAFT, InspectionStatus.IN_PROGRESS)

    def can_submit(self) -> bool:
        return self in (InspectionStatus.DRAFT, InspectionStatus.IN_PROGRESS)

    def can_close(self) -> bool:
        return self == InspectionStatus.SUBMITTED
