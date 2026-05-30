from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from src.application.ports.changeset_repository import ChangeSetRepository
from src.application.ports.inspection_repository import InspectionRepository


class UnitOfWork(ABC):
    inspections: InspectionRepository
    changesets: ChangeSetRepository

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...
