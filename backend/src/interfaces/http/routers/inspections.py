from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.application.dto.create_inspection_dto import CreateInspectionInput
from src.application.dto.edit_inspection_dto import EditInspectionInput
from src.application.dto.get_inspection_dto import GetInspectionInput
from src.application.dto.list_inspections_dto import ListInspectionsInput
from src.application.use_cases.create_inspection import CreateInspection
from src.application.use_cases.edit_inspection import EditInspection
from src.application.use_cases.get_inspection import GetInspection
from src.application.use_cases.list_inspections import ListInspections
from src.domain.exceptions import DomainError, InspectionNotFoundError, InvalidStateError
from src.interfaces.http.deps import AuditRepoDep, AuthContextDep, ClockDep, UnitOfWorkDep
from src.interfaces.http.schemas.inspection import (
    CreateInspectionRequest,
    EditInspectionRequest,
    InspectionDetailResponse,
    InspectionListResponse,
    InspectionMutationResponse,
)

router = APIRouter(prefix="/inspections", tags=["inspections"])


def _raise_domain_error(exc: DomainError) -> NoReturn:
    if isinstance(exc, InspectionNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, InvalidStateError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "",
    response_model=InspectionMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_inspection(
    body: CreateInspectionRequest,
    auth: AuthContextDep,
    uow: UnitOfWorkDep,
    clock: ClockDep,
    audit_repo: AuditRepoDep,
) -> InspectionMutationResponse:
    use_case = CreateInspection(uow=uow, clock=clock, audit_repo=audit_repo)
    output = await use_case.execute(
        CreateInspectionInput(
            title=body.title,
            location=body.location,
            user_id=auth.current_user_id(),
        )
    )
    return InspectionMutationResponse(
        inspection_id=output.inspection_id,
        version=output.version,
        status=output.status,
    )


@router.get("", response_model=InspectionListResponse)
async def list_inspections(
    auth: AuthContextDep,
    uow: UnitOfWorkDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    created_by: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InspectionListResponse:
    auth.current_user_id()
    use_case = ListInspections(uow=uow)
    try:
        output = await use_case.execute(
            ListInspectionsInput(
                status=status_filter,
                created_by=created_by,
                limit=limit,
                offset=offset,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return InspectionListResponse.from_output(output)


@router.get("/{inspection_id}", response_model=InspectionDetailResponse)
async def get_inspection(
    inspection_id: UUID,
    auth: AuthContextDep,
    uow: UnitOfWorkDep,
) -> InspectionDetailResponse:
    auth.current_user_id()
    use_case = GetInspection(uow=uow)
    try:
        output = await use_case.execute(GetInspectionInput(inspection_id=inspection_id))
    except DomainError as exc:
        _raise_domain_error(exc)
    return InspectionDetailResponse.from_output(output)


@router.patch("/{inspection_id}", response_model=InspectionMutationResponse)
async def edit_inspection(
    inspection_id: UUID,
    body: EditInspectionRequest,
    auth: AuthContextDep,
    uow: UnitOfWorkDep,
    clock: ClockDep,
) -> InspectionMutationResponse:
    use_case = EditInspection(uow=uow, clock=clock)
    try:
        output = await use_case.execute(
            EditInspectionInput(
                inspection_id=inspection_id,
                user_id=auth.current_user_id(),
                title=body.title,
                location=body.location,
            )
        )
    except DomainError as exc:
        _raise_domain_error(exc)
    return InspectionMutationResponse(
        inspection_id=output.inspection_id,
        version=output.version,
        status=output.status,
    )
