from typing import NewType
from uuid import UUID

InspectionId = NewType("InspectionId", UUID)
ObservationId = NewType("ObservationId", UUID)
EvidenceId = NewType("EvidenceId", UUID)
UserId = NewType("UserId", UUID)
