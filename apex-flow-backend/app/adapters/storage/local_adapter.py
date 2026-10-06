import os
from pathlib import Path
from app.adapters.storage.base import BaseStorageAdapter
from app.core.config import settings


class LocalStorageAdapter(BaseStorageAdapter):
    """Local file system storage adapter with atomic writes and 2MB payload ceiling."""

    def __init__(self, base_dir: str = ".apexflow_storage"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, storage_key: str) -> Path:
        # Prevent path traversal vulnerabilities
        clean_key = storage_key.lstrip("/")
        target = (self.base_dir / clean_key).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise ValueError(f"Invalid storage key path traversal: {storage_key}")
        return target

    async def save(
        self, storage_key: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        # Enforce single payload ceiling (2 MB max)
        if len(content) > settings.PAYLOAD_MAX_SINGLE_BYTES:
            raise ValueError(
                f"Payload size ({len(content)} bytes) exceeds maximum single payload limit ({settings.PAYLOAD_MAX_SINGLE_BYTES} bytes)."
            )

        target_path = self._get_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write pattern: write to .tmp file first, then atomic rename
        tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")
        with open(tmp_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, target_path)
        return storage_key

    async def get(self, storage_key: str) -> bytes:
        target_path = self._get_path(storage_key)
        if not target_path.exists():
            raise FileNotFoundError(f"Storage object '{storage_key}' not found.")
        with open(target_path, "rb") as f:
            return f.read()

    async def exists(self, storage_key: str) -> bool:
        target_path = self._get_path(storage_key)
        return target_path.exists()

    async def delete(self, storage_key: str) -> bool:
        target_path = self._get_path(storage_key)
        if target_path.exists():
            target_path.unlink()
            return True
        return False

