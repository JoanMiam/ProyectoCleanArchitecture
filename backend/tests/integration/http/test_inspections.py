from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.application.ports.file_storage_gateway import FileStorageGateway
from src.config.settings import Settings, get_settings
from src.domain.entities.inspection import Inspection
from src.domain.value_objects.ids import InspectionId, UserId
from src.infrastructure.auth.password_hasher import BcryptPasswordHasher
from src.infrastructure.persistence.sqlalchemy import SQLAlchemyUnitOfWork
from src.infrastructure.persistence.sqlalchemy.models import Base, UserModel
from src.infrastructure.persistence.sqlalchemy.session import (
    make_engine,
    make_session_factory,
)
from src.interfaces.http.deps import get_db_session, get_file_storage_gateway, get_unit_of_work
from src.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
USER_EMAIL = "inspector@example.com"
USER_PASSWORD = "hunter2"


class FakeStorageGateway(FileStorageGateway):
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, content: bytes, content_type: str) -> str:
        self.objects[key] = (content, content_type)
        return key

    async def get(self, key: str) -> bytes:
        return self.objects[key][0]

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return f"https://storage.local/{key}?expires={expires_in}"

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = make_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return make_session_factory(engine)


@pytest_asyncio.fixture
async def seed_user(session_factory: async_sessionmaker[AsyncSession]) -> UserModel:
    hasher = BcryptPasswordHasher(rounds=4)
    now = datetime.now(UTC)
    user = UserModel(
        id=uuid4(),
        email=USER_EMAIL,
        password_hash=hasher.hash(USER_PASSWORD),
        role="inspector",
        created_at=now,
        updated_at=now,
    )
    async with session_factory() as session:
        session.add(user)
        await session.commit()
    return user


@pytest.fixture
def client(session_factory: async_sessionmaker[AsyncSession]) -> Iterator[TestClient]:
    async def _override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    def _override_uow() -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(session_factory)

    app.dependency_overrides[get_db_session] = _override_session
    app.dependency_overrides[get_unit_of_work] = _override_uow
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_unit_of_work, None)


@pytest.fixture
def auth_headers(client: TestClient, seed_user: UserModel) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_get_inspection(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Factory floor", "location": "Building A"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["status"] == "draft"
    assert created_body["version"] == 0

    fetched = client.get(
        f"/inspections/{created_body['inspection_id']}",
        headers=auth_headers,
    )
    assert fetched.status_code == 200
    fetched_body = fetched.json()
    assert fetched_body["title"] == "Factory floor"
    assert fetched_body["location"] == "Building A"
    assert fetched_body["observations"] == []


def test_list_and_patch_inspections(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Initial", "location": "North wing"},
        headers=auth_headers,
    ).json()

    edited = client.patch(
        f"/inspections/{created['inspection_id']}",
        json={"title": "Updated"},
        headers=auth_headers,
    )
    assert edited.status_code == 200
    assert edited.json()["version"] == 1

    listed = client.get("/inspections", headers=auth_headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["count"] == 1
    assert body["items"][0]["title"] == "Updated"


def test_patch_inspection_requires_editable_field(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Initial", "location": "North wing"},
        headers=auth_headers,
    ).json()

    edited = client.patch(
        f"/inspections/{created['inspection_id']}",
        json={},
        headers=auth_headers,
    )

    assert edited.status_code == 422

    fetched = client.get(f"/inspections/{created['inspection_id']}", headers=auth_headers)
    assert fetched.json()["version"] == 0


def test_inspection_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/inspections")

    assert response.status_code == 401


def test_attach_evidence_uploads_file(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Factory floor", "location": "Building A"},
        headers=auth_headers,
    ).json()
    storage = FakeStorageGateway()
    app.dependency_overrides[get_file_storage_gateway] = lambda: storage
    content = b"evidence-bytes"

    try:
        response = client.post(
            f"/inspections/{created['inspection_id']}/evidences",
            files={"file": ("photo.png", content, "image/png")},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_file_storage_gateway, None)

    assert response.status_code == 201
    body = response.json()
    assert body["inspection_id"] == created["inspection_id"]
    assert body["mime_type"] == "image/png"
    assert body["file_size_bytes"] == len(content)
    assert body["sha256"] == hashlib.sha256(content).hexdigest()
    assert body["version"] == 1
    assert body["storage_key"] in storage.objects

    fetched = client.get(
        f"/inspections/{created['inspection_id']}",
        headers=auth_headers,
    )
    assert fetched.json()["evidence_count"] == 1


def test_attach_evidence_rejects_unsupported_mime_type(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Factory floor", "location": "Building A"},
        headers=auth_headers,
    ).json()
    storage = FakeStorageGateway()
    app.dependency_overrides[get_file_storage_gateway] = lambda: storage

    try:
        response = client.post(
            f"/inspections/{created['inspection_id']}/evidences",
            files={"file": ("payload.exe", b"binary", "application/x-msdownload")},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_file_storage_gateway, None)

    assert response.status_code == 415
    assert storage.objects == {}


def test_attach_evidence_rejects_closed_inspection_without_uploading(
    client: TestClient,
    auth_headers: dict[str, str],
    seed_user: UserModel,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC)
    inspection = Inspection.create(
        id=InspectionId(uuid4()),
        title="Closed inspection",
        location="Building A",
        created_by=UserId(seed_user.id),
        now=now,
    )
    inspection.submit(actor=UserId(seed_user.id), now=now)
    inspection.close(actor=UserId(seed_user.id), now=now)
    async_uow = SQLAlchemyUnitOfWork(session_factory)
    client.portal.call(_save_inspection, async_uow, inspection)
    storage = FakeStorageGateway()
    app.dependency_overrides[get_file_storage_gateway] = lambda: storage

    try:
        response = client.post(
            f"/inspections/{inspection.id}/evidences",
            files={"file": ("photo.png", b"content", "image/png")},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_file_storage_gateway, None)

    assert response.status_code == 409
    assert storage.objects == {}


def test_attach_evidence_rejects_invalid_observation_without_uploading(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Factory floor", "location": "Building A"},
        headers=auth_headers,
    ).json()
    storage = FakeStorageGateway()
    app.dependency_overrides[get_file_storage_gateway] = lambda: storage

    try:
        response = client.post(
            f"/inspections/{created['inspection_id']}/evidences",
            data={"observation_id": str(uuid4())},
            files={"file": ("photo.png", b"content", "image/png")},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_file_storage_gateway, None)

    assert response.status_code == 404
    assert storage.objects == {}


def test_attach_evidence_rejects_file_over_size_limit(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Factory floor", "location": "Building A"},
        headers=auth_headers,
    ).json()
    storage = FakeStorageGateway()
    app.dependency_overrides[get_file_storage_gateway] = lambda: storage
    app.dependency_overrides[get_settings] = lambda: Settings(evidence_max_file_size_bytes=4)

    try:
        response = client.post(
            f"/inspections/{created['inspection_id']}/evidences",
            files={"file": ("photo.png", b"12345", "image/png")},
            headers=auth_headers,
        )
    finally:
        app.dependency_overrides.pop(get_file_storage_gateway, None)
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 413
    assert storage.objects == {}


async def _save_inspection(uow: SQLAlchemyUnitOfWork, inspection: Inspection) -> None:
    async with uow:
        await uow.inspections.save(inspection)
        await uow.commit()


def test_sync_batch_updates_inspection_idempotently(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Offline title", "location": "Warehouse"},
        headers=auth_headers,
    ).json()
    change_id = str(uuid4())
    batch = {
        "batch_id": str(uuid4()),
        "client_id": "web-client",
        "changes": [
            {
                "id": change_id,
                "entity_id": created["inspection_id"],
                "entity_type": "inspection",
                "operation": "update",
                "base_version": 0,
                "payload": {"title": "Synced title"},
                "created_at": datetime.now(UTC).isoformat(),
            }
        ],
    }

    first = client.post("/sync/batch", json=batch, headers=auth_headers)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["status"] == "success"
    assert first_body["applied_changes"][0]["change_id"] == change_id
    assert first_body["applied_changes"][0]["new_version"] == 1

    second = client.post("/sync/batch", json=batch, headers=auth_headers)
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["applied_changes"][0]["new_version"] == 1
    assert second_body["server_delta"] == first_body["server_delta"]

    fetched = client.get(f"/inspections/{created['inspection_id']}", headers=auth_headers)
    assert fetched.json()["title"] == "Synced title"
    assert fetched.json()["version"] == 1


def test_sync_batch_requires_authentication(client: TestClient) -> None:
    batch = {
        "batch_id": str(uuid4()),
        "client_id": "web-client",
        "changes": [
            {
                "id": str(uuid4()),
                "entity_id": str(uuid4()),
                "entity_type": "inspection",
                "operation": "update",
                "base_version": 0,
                "payload": {"title": "Should not apply"},
                "created_at": datetime.now(UTC).isoformat(),
            }
        ],
    }

    response = client.post("/sync/batch", json=batch)

    assert response.status_code == 401


def test_sync_batch_reports_version_conflict(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Current title", "location": "Warehouse"},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/inspections/{created['inspection_id']}",
        json={"title": "Server title"},
        headers=auth_headers,
    )
    batch = {
        "batch_id": str(uuid4()),
        "client_id": "web-client",
        "changes": [
            {
                "id": str(uuid4()),
                "entity_id": created["inspection_id"],
                "entity_type": "inspection",
                "operation": "update",
                "base_version": 0,
                "payload": {"title": "Offline title"},
                "created_at": datetime.now(UTC).isoformat(),
            }
        ],
    }

    response = client.post("/sync/batch", json=batch, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "conflict"
    assert body["applied_changes"] == []
    rejected = body["rejected_changes"][0]
    assert rejected["reason"] == "version_mismatch"
    assert rejected["conflict"]["server_version"] == 1
    assert rejected["conflict"]["server_state"]["title"] == "Server title"
    assert "_events" not in rejected["conflict"]["server_state"]


def test_sync_batch_rejects_unsupported_operation_without_mutating(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Offline title", "location": "Warehouse"},
        headers=auth_headers,
    ).json()
    batch = {
        "batch_id": str(uuid4()),
        "client_id": "web-client",
        "changes": [
            {
                "id": str(uuid4()),
                "entity_id": created["inspection_id"],
                "entity_type": "inspection",
                "operation": "delete",
                "base_version": 0,
                "payload": {},
                "created_at": datetime.now(UTC).isoformat(),
            }
        ],
    }

    response = client.post("/sync/batch", json=batch, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] != "success"
    assert body["applied_changes"] == []
    assert body["rejected_changes"][0]["reason"] == "unsupported_operation"

    fetched = client.get(f"/inspections/{created['inspection_id']}", headers=auth_headers)
    assert fetched.json()["version"] == 0


def test_sync_batch_rejects_unsupported_entity_type(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    batch = {
        "batch_id": str(uuid4()),
        "client_id": "web-client",
        "changes": [
            {
                "id": str(uuid4()),
                "entity_id": str(uuid4()),
                "entity_type": "observation",
                "operation": "update",
                "base_version": 0,
                "payload": {"title": "Unsupported"},
                "created_at": datetime.now(UTC).isoformat(),
            }
        ],
    }

    response = client.post("/sync/batch", json=batch, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] != "success"
    assert body["applied_changes"] == []
    assert body["rejected_changes"][0]["reason"] == "unsupported_entity_type"


def test_sync_batch_rejects_missing_entity(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    batch = {
        "batch_id": str(uuid4()),
        "client_id": "web-client",
        "changes": [
            {
                "id": str(uuid4()),
                "entity_id": str(uuid4()),
                "entity_type": "inspection",
                "operation": "update",
                "base_version": 0,
                "payload": {"title": "Ghost title"},
                "created_at": datetime.now(UTC).isoformat(),
            }
        ],
    }

    response = client.post("/sync/batch", json=batch, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] != "success"
    assert body["applied_changes"] == []
    assert body["rejected_changes"][0]["reason"] == "entity_not_found"


def test_sync_batch_rejects_empty_update_payload_without_mutating(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Offline title", "location": "Warehouse"},
        headers=auth_headers,
    ).json()
    batch = {
        "batch_id": str(uuid4()),
        "client_id": "web-client",
        "changes": [
            {
                "id": str(uuid4()),
                "entity_id": created["inspection_id"],
                "entity_type": "inspection",
                "operation": "update",
                "base_version": 0,
                "payload": {},
                "created_at": datetime.now(UTC).isoformat(),
            }
        ],
    }

    response = client.post("/sync/batch", json=batch, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] != "success"
    assert body["applied_changes"] == []
    assert body["rejected_changes"][0]["reason"] == "empty_update_payload"

    fetched = client.get(f"/inspections/{created['inspection_id']}", headers=auth_headers)
    assert fetched.json()["version"] == 0


def test_sync_batch_rejects_invalid_update_payload_without_mutating(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/inspections",
        json={"title": "Offline title", "location": "Warehouse"},
        headers=auth_headers,
    ).json()
    batch = {
        "batch_id": str(uuid4()),
        "client_id": "web-client",
        "changes": [
            {
                "id": str(uuid4()),
                "entity_id": created["inspection_id"],
                "entity_type": "inspection",
                "operation": "update",
                "base_version": 0,
                "payload": {"title": 123},
                "created_at": datetime.now(UTC).isoformat(),
            }
        ],
    }

    response = client.post("/sync/batch", json=batch, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] != "success"
    assert body["applied_changes"] == []
    assert body["rejected_changes"][0]["reason"] == "invalid_payload"

    fetched = client.get(f"/inspections/{created['inspection_id']}", headers=auth_headers)
    assert fetched.json()["version"] == 0
