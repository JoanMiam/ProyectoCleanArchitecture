from abc import ABC, abstractmethod
from uuid import UUID


class AuthContext(ABC):
    @abstractmethod
    def current_user_id(self) -> UUID: ...

    @abstractmethod
    def has_role(self, role: str) -> bool: ...
