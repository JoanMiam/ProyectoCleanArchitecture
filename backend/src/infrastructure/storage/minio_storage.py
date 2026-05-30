from __future__ import annotations

import asyncio
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.application.ports.file_storage_gateway import FileStorageGateway


class MinIOStorageGateway(FileStorageGateway):
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        client: Any | None = None,
    ) -> None:
        self._bucket = bucket
        self._client = client or boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
            config=Config(signature_version="s3v4"),
        )

    async def put(self, key: str, content: bytes, content_type: str) -> str:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return key

    async def get(self, key: str) -> bytes:
        def _get_object() -> bytes:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            body = response["Body"]
            try:
                content = body.read()
                if not isinstance(content, bytes):
                    raise TypeError("Storage object body must be bytes.")
                return content
            finally:
                close = getattr(body, "close", None)
                if callable(close):
                    close()

        return await asyncio.to_thread(_get_object)

    async def exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(self._client.head_object, Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if self._is_not_found(exc):
                return False
            raise
        return True

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        url = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return str(url)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)

    @staticmethod
    def _is_not_found(exc: ClientError) -> bool:
        error = exc.response.get("Error", {})
        code = error.get("Code")
        return code in {"404", "NoSuchKey", "NotFound"}
