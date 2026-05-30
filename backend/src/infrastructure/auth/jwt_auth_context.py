"""Request-scoped :class:`AuthContext` built from decoded token claims.

The HTTP layer decodes the Bearer token, then constructs one of these and
passes it to use cases. The class itself is framework-free.
"""

from __future__ import annotations

from uuid import UUID

from src.application.ports.auth_context import AuthContext
from src.application.ports.token_provider import TokenClaims


class JwtAuthContext(AuthContext):
    def __init__(self, claims: TokenClaims) -> None:
        self._claims = claims

    @classmethod
    def from_claims(cls, claims: TokenClaims) -> JwtAuthContext:
        return cls(claims)

    def current_user_id(self) -> UUID:
        return self._claims.user_id

    def has_role(self, role: str) -> bool:
        return self._claims.role == role