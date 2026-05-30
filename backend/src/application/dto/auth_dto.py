"""DTOs for authentication use cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginInput:
    email: str
    password: str


@dataclass(frozen=True)
class LoginOutput:
    access_token: str
    token_type: str = "bearer"