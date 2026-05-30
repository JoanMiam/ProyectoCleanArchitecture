"""Port for password hashing and verification.

Implementations live in infrastructure (``BcryptPasswordHasher``). The use case
(``Login``) depends on this abstraction, not on bcrypt or passlib directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Return a hash of ``plain_password`` suitable for storage."""

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Return True iff ``plain_password`` matches ``hashed_password``."""