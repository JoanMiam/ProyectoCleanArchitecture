class DomainError(Exception):
    """Base for all domain errors."""


class InvalidStateError(DomainError):
    """Operation not allowed in current aggregate state."""


class InspectionNotFound(DomainError):
    """Inspection does not exist."""


class ObservationNotFound(DomainError):
    """Observation does not exist in this inspection."""


class EvidenceNotFound(DomainError):
    """Evidence reference does not exist."""


class InvariantViolation(DomainError):
    """A domain invariant was violated."""
