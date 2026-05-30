"""Pure mappers between :class:`User` (domain) and ``UserModel`` (ORM)."""

from __future__ import annotations

from datetime import UTC, datetime

from src.domain.entities.user import User
from src.domain.value_objects.ids import UserId
from src.infrastructure.persistence.sqlalchemy.models.user_model import UserModel


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def user_to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        email=user.email,
        password_hash=user.password_hash,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def user_to_domain(model: UserModel) -> User:
    return User(
        id=UserId(model.id),
        email=model.email,
        password_hash=model.password_hash,
        role=model.role,
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
    )