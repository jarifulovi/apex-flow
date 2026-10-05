from abc import ABC, abstractmethod
from typing import Optional


class BaseStorageAdapter(ABC):
    """Abstract base class for storage adapters (Local volume, S3, MinIO, etc.)."""

    @abstractmethod
    async def save(
        self, storage_key: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Save content to storage key and return stored URI or reference key."""
        pass

    @abstractmethod
    async def get(self, storage_key: str) -> bytes:
        """Retrieve binary content for the given storage key."""
        pass

    @abstractmethod
    async def exists(self, storage_key: str) -> bool:
        """Check if content exists at the storage key."""
        pass

    @abstractmethod
    async def delete(self, storage_key: str) -> bool:
        """Delete storage object at key."""
        pass
