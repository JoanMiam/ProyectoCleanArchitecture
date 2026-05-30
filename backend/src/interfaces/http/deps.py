"""FastAPI dependency providers.

Every singleton (password hasher, token provider) is exposed through a small
zero-arg callable so tests can swap it via ``app.dependency_overrides[...]``.

We use :class:`typing.Annotated` to attach ``Depends(...)`` to parameter types
(the FastAPI-recommended modern style); this avoids putting function calls in
default arguments (ruff B008).

The current scope of this file is the auth wiring required by INS-14:
- password hasher and token provider as singletons
- a session-scoped user repository
- ``get_current_auth_context`` that decodes the Bearer token and returns an
  :class:`AuthContext` ready for use cases

INS-8 will extend this file with use-case and UnitOfWork dependencies.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.auth_context import AuthContext
from src.application.ports.clock import Clock
from src.application.ports.file_storage_gateway import FileStorageGateway
from src.application.ports.password_hasher import PasswordHasher
from src.application.ports.token_provider import InvalidTokenError, TokenProvider
from src.application.ports.unit_of_work import UnitOfWork
from src.application.ports.user_repository import UserRepository
from src.config.settings import Settings, get_settings
from src.infrastructure.auth.jwt_auth_context import JwtAuthContext
from src.infrastructure.auth.jwt_provider import JwtTokenProvider
from src.infrastructure.auth.password_hasher import BcryptPasswordHasher
from src.infrastructure.clock import SystemClock
from src.infrastructure.persistence.sqlalchemy import SQLAlchemyUnitOfWork
from src.infrastructure.persistence.sqlalchemy.session import get_session_factory
from src.infrastructure.persistence.sqlalchemy.user_repository import SQLAlchemyUserRepository
from src.infrastructure.storage.minio_storage import MinIOStorageGateway

_BEARER_PREFIX = "Bearer "


# ----------------------------------------------------------------------
# Singletons (overridable in tests via app.dependency_overrides)
# ----------------------------------------------------------------------


def get_password_hasher() -> PasswordHasher:
    return BcryptPasswordHasher()


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_token_provider(settings: SettingsDep) -> TokenProvider:
    return JwtTokenProvider(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        ttl_minutes=settings.jwt_expire_minutes,
    )


def get_file_storage_gateway(settings: SettingsDep) -> FileStorageGateway:
    return MinIOStorageGateway(
        endpoint_url=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
    )


# ----------------------------------------------------------------------
# Per-request scoped
# ----------------------------------------------------------------------


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an async session for the duration of the request."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_user_repository(session: SessionDep) -> UserRepository:
    return SQLAlchemyUserRepository(session)


def get_unit_of_work() -> UnitOfWork:
    return SQLAlchemyUnitOfWork(get_session_factory())


def get_clock() -> Clock:
    return SystemClock()


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]
ClockDep = Annotated[Clock, Depends(get_clock)]
FileStorageGatewayDep = Annotated[FileStorageGateway, Depends(get_file_storage_gateway)]


# ----------------------------------------------------------------------
# Auth resolution
# ----------------------------------------------------------------------


TokenProviderDep = Annotated[TokenProvider, Depends(get_token_provider)]


def get_current_auth_context(
    tokens: TokenProviderDep,
    authorization: Annotated[str | None, Header()] = None,
) -> AuthContext:
    """Decode the Bearer token and return an :class:`AuthContext`.

    Raises ``401`` if the header is missing, malformed, or the token is
    invalid / expired.
    """
    if not authorization or not authorization.startswith(_BEARER_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len(_BEARER_PREFIX) :].strip()
    try:
        claims = tokens.decode(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return JwtAuthContext.from_claims(claims)


AuthContextDep = Annotated[AuthContext, Depends(get_current_auth_context)]
