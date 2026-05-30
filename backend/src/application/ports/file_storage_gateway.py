from abc import ABC, abstractmethod


class FileStorageGateway(ABC):
    """Stores and retrieves evidence files without coupling use cases to a backend.

    The concrete adapter targets S3-compatible object storage (MinIO), but the
    domain only knows this contract: a storage_key identifies a stored object.
    """

    @abstractmethod
    async def put(self, key: str, content: bytes, content_type: str) -> str: ...

    @abstractmethod
    async def get(self, key: str) -> bytes: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...
