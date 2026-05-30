"""Port for access token issuance and decoding.

The concrete adapter (``JwtTokenProvider``) signs and verifies JWTs with HS256.
Use cases consume this port so signing logic stays out of the application layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from src.domain.value_objects.ids import UserId


@dataclass(frozen=True)
class TokenClaims:
    """The minimal claims a decoded token must expose to the application."""

    user_id: UserId
    role: str
    issued_at: datetime
    expires_at: datetime


class InvalidTokenError(Exception):
    """Raised when a token is missing, malformed, expired or signed with the wrong key."""


class TokenProvider(ABC):
    @abstractmethod
    def issue(self, user_id: UserId, role: str, now: datetime) -> str:
        """Return a signed access token for ``user_id`` valid from ``now``."""

    @abstractmethod
    def decode(self, token: str) -> TokenClaims:
        """Return the claims carried by ``token``.

        Raises:
            InvalidTokenError: if the token is malformed, expired or has a bad signature.
        """