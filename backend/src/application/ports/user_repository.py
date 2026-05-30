"""Port to load users from persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.user import User
from src.domain.value_objects.ids import UserId


class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Return the user with ``email`` or ``None`` if not found."""

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None:
        """Return the user with ``user_id`` or ``None`` if not found."""