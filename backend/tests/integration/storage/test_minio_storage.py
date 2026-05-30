from __future__ import annotations

from typing import Any

import pytest
from botocore.exceptions import ClientError

from src.infrastructure.storage.minio_storage import MinIOStorageGateway


class FakeBody:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self.closed = False

    def read(self) -> bytes:
        return self._content

    def close(self) -> None:
        self.closed = True


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, str]] = {}
        self.last_body: FakeBody | None = None

    def put_object(self, **kwargs: Any) -> None:
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = (
            kwargs["Body"],
            kwargs["ContentType"],
        )

    def get_object(self, **kwargs: Any) -> dict[str, FakeBody]:
        content, _ = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        self.last_body = FakeBody(content)
        return {"Body": self.last_body}

    def head_object(self, **kwargs: Any) -> None:
        if (kwargs["Bucket"], kwargs["Key"]) not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")

    def generate_presigned_url(self, operation: str, **kwargs: Any) -> str:
        params = kwargs["Params"]
        return (
            f"https://storage.local/{operation}/{params['Bucket']}/{params['Key']}"
            f"?expires={kwargs['ExpiresIn']}"
        )

    def delete_object(self, **kwargs: Any) -> None:
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_minio_gateway_stores_reads_signs_and_deletes_objects() -> None:
    client = FakeS3Client()
    gateway = MinIOStorageGateway(
        endpoint_url="http://minio:9000",
        access_key="minioadmin",
        secret_key="minioadmin123",
        bucket="evidences",
        client=client,
    )

    key = await gateway.put("inspections/1/evidences/2/photo.png", b"image", "image/png")

    assert key == "inspections/1/evidences/2/photo.png"
    assert await gateway.exists(key) is True
    assert await gateway.get(key) == b"image"
    assert client.last_body is not None
    assert client.last_body.closed is True
    assert await gateway.generate_presigned_url(key, expires_in=60) == (
        "https://storage.local/get_object/evidences/inspections/1/evidences/2/photo.png?expires=60"
    )

    await gateway.delete(key)

    assert await gateway.exists(key) is False
