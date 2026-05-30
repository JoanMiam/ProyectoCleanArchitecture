from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.application.ports.conflict_repository import ConflictRepository
from src.application.ports.unit_of_work import UnitOfWork
from src.domain.value_objects.ids import InspectionId


class ResolveConflict:
    def __init__(self, uow: UnitOfWork, conflict_repo: ConflictRepository) -> None:
        self.uow = uow
        self.conflict_repo = conflict_repo

    async def execute(
        self, 
        change_id: UUID, 
        strategy: str, 
        payload: dict[str, Any] | None = None
    ) -> None:
        async with self.uow:
            # 1. Obtener el conflicto (para saber qué entidad es)
            # En un sistema real, list_unresolved filtraría por change_id
            # Para este MVP, asumimos que el repositorio puede darnos el detalle
            conflicts = await self.conflict_repo.list_unresolved()
            conflict = next((c for c in conflicts if c.change_id == change_id), None)
            
            if not conflict:
                raise ValueError(f"Conflict for change {change_id} not found or already resolved")

            if strategy in ["keep_client", "manual_merge"]:
                if not payload:
                    raise ValueError(f"Payload required for strategy {strategy}")
                
                if conflict.entity_type == "inspection":
                    inspection_id = InspectionId(conflict.entity_id)
                    inspection = await self.uow.inspections.get(inspection_id)
                    
                    inspection.edit(
                        title=payload.get("title"),
                        location=payload.get("location"),
                        now=datetime.now(UTC).replace(tzinfo=None)
                    )
                    await self.uow.inspections.save(inspection)

            # Marcar como resuelto
            await self.conflict_repo.mark_resolved(change_id, strategy)
            await self.uow.commit()
