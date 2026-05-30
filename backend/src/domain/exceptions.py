class DomainError(Exception):
    """Base for all domain errors."""


class InvalidStateError(DomainError):
    """Operation not allowed in current aggregate state."""


class InspectionNotFoundError(DomainError):
    """Inspection does not exist."""


class ObservationNotFoundError(DomainError):
    """Observation does not exist in this inspection."""


class EvidenceNotFoundError(DomainError):
    """Evidence reference does not exist."""


class InvariantViolationError(DomainError):
    """A domain invariant was violated."""
