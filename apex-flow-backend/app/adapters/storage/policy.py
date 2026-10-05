import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union
from app.core.config import settings
from app.adapters.storage.base import BaseStorageAdapter
from app.adapters.storage.local_adapter import LocalStorageAdapter
from app.adapters.storage.s3_adapter import S3StorageAdapter


_adapter_instance: Optional[BaseStorageAdapter] = None


def get_storage_adapter() -> BaseStorageAdapter:
    """Returns configured storage adapter instance (Singleton)."""
    global _adapter_instance
    if _adapter_instance is not None:
        return _adapter_instance

    if settings.STORAGE_PROVIDER == "s3" and settings.S3_BUCKET_NAME:
        try:
            _adapter_instance = S3StorageAdapter(
                bucket_name=settings.S3_BUCKET_NAME,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                endpoint_url=settings.S3_ENDPOINT_URL,
                region_name=settings.AWS_REGION,
            )
            return _adapter_instance
        except Exception:
            # Fallback to local storage if S3 initialization fails
            pass

    _adapter_instance = LocalStorageAdapter(base_dir=settings.STORAGE_LOCAL_DIR)
    return _adapter_instance


class PayloadPolicyManager:
    """Policy manager for inspecting, offloading, and dereferencing payloads."""

    REF_KEY = "$apexflow_ref"

    @classmethod
    def is_ref(cls, obj: Any) -> bool:
        """Check if an object is an ApexFlow storage reference descriptor."""
        return isinstance(obj, dict) and obj.get(cls.REF_KEY) is True

    @classmethod
    def serialize_payload(cls, payload: Any) -> Tuple[bytes, str]:
        """Convert arbitrary payload (dict, list, str, bytes) into binary blob and content_type."""
        if isinstance(payload, bytes):
            return payload, "application/octet-stream"
        elif isinstance(payload, str):
            return payload.encode("utf-8"), "text/plain"
        else:
            # JSON dict or list
            json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            return json_bytes, "application/json"

    @classmethod
    def should_offload(cls, payload: Any) -> bool:
        """Check if payload size exceeds threshold (default 250KB)."""
        if cls.is_ref(payload):
            return False
        blob, _ = cls.serialize_payload(payload)
        return len(blob) > settings.PAYLOAD_MAX_INLINE_BYTES

    @classmethod
    def create_ref(
        cls,
        storage_key: str,
        size_bytes: int,
        content_type: str,
        filename: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build canonical reference descriptor."""
        return {
            cls.REF_KEY: True,
            "key": storage_key,
            "size_bytes": size_bytes,
            "content_type": content_type,
            "filename": filename or storage_key.split("/")[-1],
            "provider": provider or settings.STORAGE_PROVIDER,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    async def process_and_offload_if_needed(
        cls, payload: Any, storage_prefix: str = "payloads"
    ) -> Tuple[Any, bool]:
        """
        If payload exceeds inline size limit, offloads it to storage adapter
        and returns (ref_dict, True). Otherwise returns (original_payload, False).
        """
        if not cls.should_offload(payload):
            return payload, False

        blob, content_type = cls.serialize_payload(payload)
        ext = ".json" if content_type == "application/json" else ".bin"
        unique_id = uuid.uuid4().hex[:12]
        key = f"{storage_prefix}/{datetime.now(timezone.utc).strftime('%Y%m%d')}_{unique_id}{ext}"

        adapter = get_storage_adapter()
        stored_key = await adapter.save(key, blob, content_type)
        ref = cls.create_ref(
            storage_key=stored_key,
            size_bytes=len(blob),
            content_type=content_type,
            provider="s3" if isinstance(adapter, S3StorageAdapter) else "local",
        )
        return ref, True
