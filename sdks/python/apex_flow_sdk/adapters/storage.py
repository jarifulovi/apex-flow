import json
from typing import Any, Tuple
import httpx


class StorageResolver:
    """Client-side adapter for detecting offload references, uploading large payloads, and resolving $apexflow_ref pointers."""

    REF_KEY = "$apexflow_ref"
    MAX_INLINE_BYTES = 250 * 1024  # 250 KB

    @classmethod
    def is_ref(cls, obj: Any) -> bool:
        """Check if an object is an ApexFlow storage reference descriptor."""
        return isinstance(obj, dict) and obj.get(cls.REF_KEY) is True

    @classmethod
    async def resolve_payload(
        cls, http_client: httpx.AsyncClient, base_url: str, payload: Any
    ) -> Any:
        """Recursively resolve $apexflow_ref descriptors back into native dicts, lists, strings, or bytes."""
        if cls.is_ref(payload):
            storage_key = payload["key"]
            res = await http_client.get(f"{base_url}/api/v1/storage/download/{storage_key}")
            res.raise_for_status()
            
            content_type = payload.get("content_type", "")
            if "application/json" in content_type or storage_key.endswith(".json"):
                return res.json()
            return res.content

        if isinstance(payload, dict):
            return {
                k: await cls.resolve_payload(http_client, base_url, v)
                for k, v in payload.items()
            }
        elif isinstance(payload, list):
            return [await cls.resolve_payload(http_client, base_url, item) for item in payload]

        return payload

    @classmethod
    async def offload_if_needed(
        cls, http_client: httpx.AsyncClient, base_url: str, payload: Any
    ) -> Tuple[Any, bool]:
        """Offload payload to control plane storage if size exceeds MAX_INLINE_BYTES (250KB)."""
        if cls.is_ref(payload):
            return payload, False

        if isinstance(payload, bytes):
            data_bytes = payload
            content_type = "application/octet-stream"
            filename = "payload.bin"
        elif isinstance(payload, str):
            data_bytes = payload.encode("utf-8")
            content_type = "text/plain"
            filename = "payload.txt"
        else:
            data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            content_type = "application/json"
            filename = "payload.json"

        if len(data_bytes) <= cls.MAX_INLINE_BYTES:
            return payload, False

        files = {"file": (filename, data_bytes, content_type)}
        res = await http_client.post(f"{base_url}/api/v1/storage/upload", files=files)
        res.raise_for_status()
        ref = res.json()
        return ref, True
