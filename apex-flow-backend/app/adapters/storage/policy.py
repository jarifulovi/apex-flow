import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union
from app.core.config import settings
from app.adapters.storage.base import BaseStorageAdapter
from app.adapters.storage.local_adapter import LocalStorageAdapter
from app.adapters.storage.s3_adapter import S3StorageAdapter


_adapter_instance: Optional[BaseStorageAdapter] = None


def reset_storage_adapter() -> None:
    """Reset the cached storage adapter instance (primarily for tests)."""
    global _adapter_instance
    _adapter_instance = None


def get_storage_adapter() -> BaseStorageAdapter:
    """Returns the configured storage adapter instance.

    Strictly two modes:
      1. 'local': Strictly for development. Storing files locally is forbidden in production
                  to prevent ephemeral container disk overflow on hosts like Render.
      2. 's3' (or 'cloudflare'): Cloudflare R2 / AWS S3 compatible storage.
                  Fails immediately if misconfigured — NO silent fallback to disk.
    """
    global _adapter_instance
    if _adapter_instance is not None:
        return _adapter_instance

    provider = (settings.STORAGE_PROVIDER or "local").strip().lower()

    if provider in ("s3", "cloudflare", "r2"):
        if not settings.S3_BUCKET_NAME:
            raise RuntimeError(
                f"STORAGE_PROVIDER is '{settings.STORAGE_PROVIDER}', but S3_BUCKET_NAME is not configured."
            )
        # S3StorageAdapter will raise directly if boto3 is missing or configuration is invalid.
        # Absolutely NO silent fallback to local disk.
        _adapter_instance = S3StorageAdapter(
            bucket_name=settings.S3_BUCKET_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.AWS_REGION or "auto",
        )
        return _adapter_instance

    if provider == "local":
        if (settings.ENVIRONMENT or "").strip().lower() == "production":
            raise RuntimeError(
                "STORAGE_PROVIDER='local' is forbidden in production environment to prevent "
                "container disk overflow. Please configure Cloudflare R2 or S3."
            )
        _adapter_instance = LocalStorageAdapter(base_dir=settings.STORAGE_LOCAL_DIR)
        return _adapter_instance

    raise ValueError(
        f"Invalid STORAGE_PROVIDER: '{settings.STORAGE_PROVIDER}'. "
        "ApexFlow supports either 'local' (dev only) or 's3'/'cloudflare' (Cloudflare R2 / AWS S3)."
    )


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
        encrypted: bool = False,
        key_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build canonical reference descriptor."""
        ref = {
            cls.REF_KEY: True,
            "key": storage_key,
            "size_bytes": size_bytes,
            "content_type": content_type,
            "filename": filename or storage_key.split("/")[-1],
            "provider": provider or settings.STORAGE_PROVIDER,
            "encrypted": encrypted,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if key_hint:
            ref["key_hint"] = key_hint
        return ref

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
        is_enc = isinstance(payload, dict) and payload.get("$apexflow_encrypted") is True
        key_hint = payload.get("key_hint") if is_enc else None
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
            encrypted=is_enc,
            key_hint=key_hint,
        )
        return ref, True
