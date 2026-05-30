from typing import NoReturn

from fastapi import APIRouter, HTTPException, status

from src.application.use_cases.apply_changes_batch import ApplyChangesBatch
from src.domain.exceptions import DomainError, InspectionNotFoundError, InvalidStateError
from src.interfaces.http.deps import AuthContextDep, UnitOfWorkDep
from src.interfaces.http.schemas.sync import SyncBatchRequest, SyncResponse

router = APIRouter(prefix="/sync", tags=["sync"])


def _raise_domain_error(exc: DomainError) -> NoReturn:
    if isinstance(exc, InspectionNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, InvalidStateError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/batch", response_model=SyncResponse)
async def apply_sync_batch(
    body: SyncBatchRequest,
    auth: AuthContextDep,
    uow: UnitOfWorkDep,
) -> SyncResponse:
    auth.current_user_id()
    use_case = ApplyChangesBatch(uow=uow)
    try:
        output = await use_case.execute(body.to_dto())
    except DomainError as exc:
        _raise_domain_error(exc)
    return SyncResponse.from_dto(output)
