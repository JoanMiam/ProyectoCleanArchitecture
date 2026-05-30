"""Pydantic schemas for the auth router.

Pydantic lives at the edge (``interfaces/http/``). The application layer
consumes plain dataclass DTOs (``auth_dto``); these schemas are only what
FastAPI uses to validate / serialize HTTP payloads.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user_id: UUID
    role: str