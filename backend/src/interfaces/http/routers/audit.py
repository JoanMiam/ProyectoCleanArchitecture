from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.application.ports.audit_repository import AuditRepository
from src.application.use_cases.get_audit_trail import GetAuditTrail, GetAuditTrailInput
from src.interfaces.http.deps import AuthContextDep, get_audit_repository
from src.interfaces.http.schemas.audit import AuditEntryResponse, AuditTrailResponse

router = APIRouter(prefix="/inspections", tags=["audit"])

AuditRepoDep = Annotated[AuditRepository, Depends(get_audit_repository)]


@router.get(
    "/{inspection_id}/audit",
    response_model=AuditTrailResponse,
    summary="Get the audit trail for an inspection",
)
async def get_audit_trail(
    inspection_id: UUID,
    auth: AuthContextDep,
    audit_repo: AuditRepoDep,
) -> AuditTrailResponse:
    auth.current_user_id()
    use_case = GetAuditTrail(audit_repo=audit_repo)
    output = await use_case.execute(GetAuditTrailInput(inspection_id=inspection_id))
    return AuditTrailResponse(
        inspection_id=inspection_id,
        entries=[
            AuditEntryResponse(
                aggregate_id=e.aggregate_id,
                aggregate_type=e.aggregate_type,
                event_type=e.event_type,
                actor_id=e.actor_id,
                occurred_at=e.occurred_at,
                payload=e.payload,
            )
            for e in output.entries
        ],
        count=len(output.entries),
    )
