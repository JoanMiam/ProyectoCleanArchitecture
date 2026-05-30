from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from src.domain.value_objects.version import Version


class ConflictType(StrEnum):
    """Why a change could not be applied cleanly under optimistic locking."""

    CONCURRENT_MODIFICATION = "concurrent_modification"
    """The client's base_version is behind the server: someone else changed
    the entity since the client last synced."""

    STALE_CLIENT = "stale_client"
    """The client's base_version is ahead of the server: an impossible state
    under normal operation (e.g. lost server write, replayed out of order)."""


class ResolutionStrategy(StrEnum):
    """How a detected conflict is meant to be resolved (applied in INS-7)."""

    KEEP_SERVER = "keep_server"
    KEEP_CLIENT = "keep_client"
    MANUAL_MERGE = "manual_merge"


class ConflictPolicy:
    """Pure rule that decides whether a change conflicts with server state.

    Optimistic locking: a change carries the base_version it was built against.
    It applies cleanly only when that base equals the server's current version.
    """

    @staticmethod
    def detect(base: Version, current: Version) -> ConflictType | None:
        if base == current:
            return None
        if base < current:
            return ConflictType.CONCURRENT_MODIFICATION
        return ConflictType.STALE_CLIENT


@dataclass(frozen=True)
class Conflict:
    """A detected conflict between a client change and authoritative server state."""

    entity_id: UUID
    entity_type: str
    base_version: Version
    current_version: Version
    type: ConflictType

    @classmethod
    def between(
        cls,
        entity_id: UUID,
        entity_type: str,
        base: Version,
        current: Version,
    ) -> Conflict | None:
        """Build a Conflict if `base` clashes with `current`, else None."""
        conflict_type = ConflictPolicy.detect(base, current)
        if conflict_type is None:
            return None
        return cls(
            entity_id=entity_id,
            entity_type=entity_type,
            base_version=base,
            current_version=current,
            type=conflict_type,
        )
