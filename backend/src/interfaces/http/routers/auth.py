"""HTTP router for authentication.

Endpoints:
- ``POST /auth/login`` — exchange credentials for a JWT.
- ``GET  /auth/me``    — example protected endpoint demonstrating that
  ``AuthContext`` is wired end-to-end. INS-8 will protect the real business
  endpoints the same way.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.dto.auth_dto import LoginInput
from src.application.ports.clock import Clock
from src.application.ports.password_hasher import PasswordHasher
from src.application.ports.token_provider import TokenProvider
from src.application.ports.user_repository import UserRepository
from src.application.use_cases.login import InvalidCredentialsError, Login
from src.infrastructure.clock import SystemClock
from src.interfaces.http.deps import (
    AuthContextDep,
    get_password_hasher,
    get_token_provider,
    get_user_repository,
)
from src.interfaces.http.schemas.auth import LoginRequest, LoginResponse, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_clock() -> Clock:
    return SystemClock()


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
TokenProviderDep = Annotated[TokenProvider, Depends(get_token_provider)]
ClockDep = Annotated[Clock, Depends(_get_clock)]


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange email + password for a JWT access token",
)
async def login(
    body: LoginRequest,
    users: UserRepositoryDep,
    hasher: PasswordHasherDep,
    tokens: TokenProviderDep,
    clock: ClockDep,
) -> LoginResponse:
    use_case = Login(users=users, hasher=hasher, tokens=tokens, clock=clock)
    try:
        result = await use_case.execute(LoginInput(email=body.email, password=body.password))
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    return LoginResponse(access_token=result.access_token, token_type=result.token_type)


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Return the authenticated user id and role (protected)",
)
async def me(auth: AuthContextDep) -> MeResponse:
    return MeResponse(
        user_id=auth.current_user_id(),
        role="admin" if auth.has_role("admin") else "inspector",
    )