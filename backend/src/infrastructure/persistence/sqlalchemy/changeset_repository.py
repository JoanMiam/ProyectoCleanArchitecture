from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.sync_dto import AppliedChangeDTO
from src.application.ports.changeset_repository import ChangeSetRepository
from src.infrastructure.persistence.sqlalchemy.models.applied_change_model import (
    AppliedChangeModel,
)


class SQLAlchemyChangeSetRepository(ChangeSetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_been_applied(self, change_id: UUID) -> bool:
        stmt = select(AppliedChangeModel.change_id).where(
            AppliedChangeModel.change_id == change_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def record_applied(self, applied: AppliedChangeDTO) -> None:
        self._session.add(
            AppliedChangeModel(
                change_id=applied.change_id,
                new_version=applied.new_version,
                server_delta=applied.server_delta,
                created_at=datetime.now(UTC),
            )
        )

    async def get_applied(self, change_id: UUID) -> AppliedChangeDTO | None:
        model = await self._session.get(AppliedChangeModel, change_id)
        if model is None:
            return None
        return AppliedChangeDTO(
            change_id=model.change_id,
            new_version=model.new_version,
            server_delta=model.server_delta,
        )
