from abc import ABC, abstractmethod
from uuid import UUID

from src.application.dto.sync_dto import ConflictResultDTO


class ConflictRepository(ABC):
    """Persists conflicts detected during sync and tracks their resolution.

    A conflict is raised when a ChangeSet's base_version is behind the server's
    current_version. It is stored as unresolved until a resolution strategy
    (keep_server, keep_client, manual_merge) is applied (INS-7).
    """

    @abstractmethod
    async def save(self, conflict: ConflictResultDTO) -> None: ...

    @abstractmethod
    async def list_unresolved(
        self, entity_id: UUID | None = None
    ) -> list[ConflictResultDTO]: ...

    @abstractmethod
    async def mark_resolved(self, change_id: UUID, resolution: str) -> None: ...
