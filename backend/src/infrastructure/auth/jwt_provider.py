"""JWT-backed implementation of :class:`TokenProvider`.

Uses ``python-jose`` (HS256). The secret and lifetime are read from settings,
which in turn load from environment variables — ``JWT_SECRET`` is never
hard-coded in the repo. The claims layout is deliberately small: ``sub`` for
the user id, ``role`` for authorization checks, plus the standard ``iat`` /
``exp`` for issued-at / expiration.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt

from src.application.ports.token_provider import (
    InvalidTokenError,
    TokenClaims,
    TokenProvider,
)
from src.domain.value_objects.ids import UserId

_ALGORITHM_KEY = "algorithm"


class JwtTokenProvider(TokenProvider):
    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        ttl_minutes: int = 60,
    ) -> None:
        if not secret:
            raise ValueError("JWT secret must be non-empty.")
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = timedelta(minutes=ttl_minutes)

    def issue(self, user_id: UserId, role: str, now: datetime) -> str:
        payload = {
            "sub": str(user_id),
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int((now + self._ttl).timestamp()),
        }
        token: str = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return token

    def decode(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except JWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        try:
            return TokenClaims(
                user_id=UserId(UUID(str(payload["sub"]))),
                role=str(payload["role"]),
                issued_at=datetime.fromtimestamp(int(payload["iat"])),
                expires_at=datetime.fromtimestamp(int(payload["exp"])),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise InvalidTokenError(f"Malformed token claims: {exc}") from exc