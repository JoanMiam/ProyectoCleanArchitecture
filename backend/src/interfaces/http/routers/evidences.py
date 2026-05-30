from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from src.application.dto.attach_evidence_dto import AttachEvidenceInput
from src.application.use_cases.attach_evidence import AttachEvidence, InvalidEvidenceError
from src.domain.exceptions import (
    DomainError,
    InspectionNotFoundError,
    InvalidStateError,
    ObservationNotFoundError,
)
from src.interfaces.http.deps import (
    AuthContextDep,
    ClockDep,
    FileStorageGatewayDep,
    SettingsDep,
    UnitOfWorkDep,
)
from src.interfaces.http.schemas.evidence import EvidenceResponse

router = APIRouter(prefix="/inspections", tags=["evidences"])


def _raise_domain_error(exc: DomainError) -> NoReturn:
    if isinstance(exc, (InspectionNotFoundError, ObservationNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, InvalidStateError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{inspection_id}/evidences",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_evidence(
    inspection_id: UUID,
    file: Annotated[UploadFile, File()],
    auth: AuthContextDep,
    uow: UnitOfWorkDep,
    clock: ClockDep,
    storage_gateway: FileStorageGatewayDep,
    settings: SettingsDep,
    observation_id: Annotated[UUID | None, Form()] = None,
) -> EvidenceResponse:
    try:
        mime_type = _normalize_mime_type(file.content_type)
        _validate_mime_type(mime_type, settings.allowed_evidence_mime_types)
        content = await _read_limited(file, settings.evidence_max_file_size_bytes)

        use_case = AttachEvidence(uow=uow, clock=clock, storage=storage_gateway)
        output = await use_case.execute(
            AttachEvidenceInput(
                inspection_id=inspection_id,
                user_id=auth.current_user_id(),
                filename=file.filename or "evidence",
                mime_type=mime_type,
                content=content,
                observation_id=observation_id,
            )
        )
        return EvidenceResponse.from_output(output)
    except InvalidEvidenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        _raise_domain_error(exc)
    finally:
        await file.close()


def _normalize_mime_type(content_type: str | None) -> str:
    if content_type is None:
        return ""
    return content_type.split(";", maxsplit=1)[0].strip().lower()


def _validate_mime_type(mime_type: str, allowed: frozenset[str]) -> None:
    if not mime_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Evidence mime type is required.",
        )
    if mime_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Evidence mime type '{mime_type}' is not allowed.",
        )


async def _read_limited(file: UploadFile, max_size_bytes: int) -> bytes:
    content = await file.read(max_size_bytes + 1)
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Evidence file exceeds the {max_size_bytes} byte limit.",
        )
    return content
