"""SQLAlchemy-backed :class:`UserRepository`.

Login does not require a transactional scope, so this repository takes a plain
``AsyncSession`` rather than living inside the ``UnitOfWork`` (which would
force every reader to open one).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.user_repository import UserRepository
from src.domain.entities.user import User
from src.domain.value_objects.ids import UserId
from src.infrastructure.persistence.sqlalchemy.mappers.user_mapper import user_to_domain
from src.infrastructure.persistence.sqlalchemy.models.user_model import UserModel


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email).limit(1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return user_to_domain(model) if model is not None else None

    async def get_by_id(self, user_id: UserId) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return user_to_domain(model) if model is not None else None