"""Login use case.

Receives credentials, looks up the user, verifies the password through the
hasher port, and issues a token through the token provider port. No framework
or library is referenced here.
"""

from __future__ import annotations

from src.application.dto.auth_dto import LoginInput, LoginOutput
from src.application.ports.clock import Clock
from src.application.ports.password_hasher import PasswordHasher
from src.application.ports.token_provider import TokenProvider
from src.application.ports.user_repository import UserRepository


class InvalidCredentialsError(Exception):
    """Raised when email is unknown or password does not match.

    The same exception is used for both cases on purpose: leaking which one
    failed enables user enumeration attacks.
    """


class Login:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenProvider,
        clock: Clock,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock

    async def execute(self, cmd: LoginInput) -> LoginOutput:
        user = await self._users.get_by_email(cmd.email)
        if user is None or not self._hasher.verify(cmd.password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")
        token = self._tokens.issue(user_id=user.id, role=user.role, now=self._clock.now())
        return LoginOutput(access_token=token)