from abc import ABC, abstractmethod
from uuid import UUID

from src.application.dto.sync_dto import AppliedChangeDTO


class ChangeSetRepository(ABC):
    """Guarantees idempotency of sync changes.

    Each ChangeSet carries a client-generated id. A resent ChangeSet must not
    be applied twice: the repository records the result of every applied change
    so a duplicate push returns the original outcome instead of mutating state.
    """

    @abstractmethod
    async def has_been_applied(self, change_id: UUID) -> bool: ...

    @abstractmethod
    async def record_applied(self, applied: AppliedChangeDTO) -> None: ...

    @abstractmethod
    async def get_applied(self, change_id: UUID) -> AppliedChangeDTO | None: ...
