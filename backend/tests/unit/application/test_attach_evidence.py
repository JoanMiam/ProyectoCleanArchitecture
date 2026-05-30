"""TDD tests for AttachEvidence use case."""

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.application.dto.attach_evidence_dto import AttachEvidenceInput
from src.application.ports.file_storage_gateway import FileStorageGateway
from src.application.use_cases.attach_evidence import AttachEvidence, InvalidEvidenceError
from src.domain.entities.inspection import Inspection
from src.domain.exceptions import InvalidStateError, ObservationNotFoundError
from src.domain.value_objects.ids import InspectionId, UserId
from tests.unit.conftest import FakeClock, FakeUnitOfWork

NOW = datetime(2026, 1, 15, 10, 0, 0, tzinfo=UTC)


class FakeStorageGateway(FileStorageGateway):
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.deleted: list[str] = []
        self.fail_put = False

    async def put(self, key: str, content: bytes, content_type: str) -> str:
        if self.fail_put:
            raise RuntimeError("storage unavailable")
        self.objects[key] = (content, content_type)
        return key

    async def get(self, key: str) -> bytes:
        return self.objects[key][0]

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return f"https://storage.local/{key}?expires={expires_in}"

    async def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)


class FailingCommitUnitOfWork(FakeUnitOfWork):
    async def commit(self) -> None:
        raise RuntimeError("commit failed")


class FailingExitUnitOfWork(FakeUnitOfWork):
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await super().__aexit__(exc_type, exc_val, None)
        raise RuntimeError("exit failed")


def _make_inspection(created_by: UUID, *, closed: bool = False) -> Inspection:
    inspection = Inspection.create(
        id=InspectionId(uuid4()),
        title="Factory Floor",
        location="Building B",
        created_by=UserId(created_by),
        now=NOW,
    )
    if closed:
        inspection.submit(actor=UserId(created_by), now=NOW)
        inspection.close(actor=UserId(created_by), now=NOW)
    return inspection


@pytest.mark.unit
class TestAttachEvidence:
    @pytest.fixture
    def storage(self) -> FakeStorageGateway:
        return FakeStorageGateway()

    @pytest.fixture
    def use_case(
        self,
        fake_uow: FakeUnitOfWork,
        fixed_clock: FakeClock,
        storage: FakeStorageGateway,
    ) -> AttachEvidence:
        return AttachEvidence(uow=fake_uow, clock=fixed_clock, storage=storage)

    @pytest.mark.asyncio
    async def test_uploads_file_and_persists_reference(
        self,
        use_case: AttachEvidence,
        fake_uow: FakeUnitOfWork,
        storage: FakeStorageGateway,
        user_id: UUID,
    ) -> None:
        inspection = _make_inspection(user_id)
        await fake_uow.inspections.save(inspection)
        content = b"image-bytes"

        output = await use_case.execute(
            AttachEvidenceInput(
                inspection_id=inspection.id,
                user_id=user_id,
                filename="photo.png",
                mime_type="image/png",
                content=content,
            )
        )

        assert output.inspection_id == inspection.id
        assert output.file_size_bytes == len(content)
        assert output.mime_type == "image/png"
        assert output.sha256 == hashlib.sha256(content).hexdigest()
        assert output.version == 1
        assert output.storage_key in storage.objects
        assert len(fake_uow.inspections._store[inspection.id].evidences) == 1
        assert fake_uow.committed is True

    @pytest.mark.asyncio
    async def test_attaches_to_existing_observation(
        self,
        use_case: AttachEvidence,
        fake_uow: FakeUnitOfWork,
        user_id: UUID,
    ) -> None:
        inspection = _make_inspection(user_id)
        observation = inspection.add_observation(
            title="Crack",
            notes="North wall",
            actor=UserId(user_id),
            now=NOW,
        )
        await fake_uow.inspections.save(inspection)

        output = await use_case.execute(
            AttachEvidenceInput(
                inspection_id=inspection.id,
                user_id=user_id,
                filename="crack.jpg",
                mime_type="image/jpeg",
                content=b"jpeg",
                observation_id=observation.id,
            )
        )

        assert output.observation_id == observation.id
        assert fake_uow.inspections._store[inspection.id].evidences[0].observation_id == (
            observation.id
        )

    @pytest.mark.asyncio
    async def test_rejects_observation_from_another_inspection_before_storage(
        self,
        use_case: AttachEvidence,
        fake_uow: FakeUnitOfWork,
        storage: FakeStorageGateway,
        user_id: UUID,
    ) -> None:
        inspection = _make_inspection(user_id)
        await fake_uow.inspections.save(inspection)

        with pytest.raises(ObservationNotFoundError):
            await use_case.execute(
                AttachEvidenceInput(
                    inspection_id=inspection.id,
                    user_id=user_id,
                    filename="photo.png",
                    mime_type="image/png",
                    content=b"content",
                    observation_id=uuid4(),
                )
            )

        assert storage.objects == {}
        assert storage.deleted == []

    @pytest.mark.asyncio
    async def test_rejects_closed_inspection_before_storage(
        self,
        use_case: AttachEvidence,
        fake_uow: FakeUnitOfWork,
        storage: FakeStorageGateway,
        user_id: UUID,
    ) -> None:
        inspection = _make_inspection(user_id, closed=True)
        await fake_uow.inspections.save(inspection)

        with pytest.raises(InvalidStateError):
            await use_case.execute(
                AttachEvidenceInput(
                    inspection_id=inspection.id,
                    user_id=user_id,
                    filename="photo.png",
                    mime_type="image/png",
                    content=b"content",
                )
            )

        assert storage.objects == {}
        assert storage.deleted == []

    @pytest.mark.asyncio
    async def test_rejects_empty_content_before_storage(
        self,
        use_case: AttachEvidence,
        storage: FakeStorageGateway,
        user_id: UUID,
    ) -> None:
        with pytest.raises(InvalidEvidenceError):
            await use_case.execute(
                AttachEvidenceInput(
                    inspection_id=uuid4(),
                    user_id=user_id,
                    filename="empty.png",
                    mime_type="image/png",
                    content=b"",
                )
            )

        assert storage.objects == {}

    @pytest.mark.asyncio
    async def test_storage_failure_does_not_commit(
        self,
        use_case: AttachEvidence,
        fake_uow: FakeUnitOfWork,
        storage: FakeStorageGateway,
        user_id: UUID,
    ) -> None:
        inspection = _make_inspection(user_id)
        await fake_uow.inspections.save(inspection)
        storage.fail_put = True

        with pytest.raises(RuntimeError, match="storage unavailable"):
            await use_case.execute(
                AttachEvidenceInput(
                    inspection_id=inspection.id,
                    user_id=user_id,
                    filename="photo.png",
                    mime_type="image/png",
                    content=b"content",
                )
            )

        assert len(fake_uow.inspections.saved) == 1
        assert fake_uow.committed is False

    @pytest.mark.asyncio
    async def test_commit_failure_cleans_uploaded_object(
        self,
        fixed_clock: FakeClock,
        storage: FakeStorageGateway,
        user_id: UUID,
    ) -> None:
        uow = FailingCommitUnitOfWork()
        inspection = _make_inspection(user_id)
        await uow.inspections.save(inspection)
        use_case = AttachEvidence(uow=uow, clock=fixed_clock, storage=storage)

        with pytest.raises(RuntimeError, match="commit failed"):
            await use_case.execute(
                AttachEvidenceInput(
                    inspection_id=inspection.id,
                    user_id=user_id,
                    filename="photo.png",
                    mime_type="image/png",
                    content=b"content",
                )
            )

        assert storage.objects == {}
        assert len(storage.deleted) == 1

    @pytest.mark.asyncio
    async def test_does_not_delete_storage_after_successful_commit(
        self,
        fixed_clock: FakeClock,
        storage: FakeStorageGateway,
        user_id: UUID,
    ) -> None:
        uow = FailingExitUnitOfWork()
        inspection = _make_inspection(user_id)
        await uow.inspections.save(inspection)
        use_case = AttachEvidence(uow=uow, clock=fixed_clock, storage=storage)

        with pytest.raises(RuntimeError, match="exit failed"):
            await use_case.execute(
                AttachEvidenceInput(
                    inspection_id=inspection.id,
                    user_id=user_id,
                    filename="photo.png",
                    mime_type="image/png",
                    content=b"content",
                )
            )

        assert len(storage.objects) == 1
        assert storage.deleted == []
