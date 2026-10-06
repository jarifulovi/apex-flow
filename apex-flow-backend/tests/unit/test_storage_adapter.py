import pytest
from pathlib import Path
from app.adapters.storage.local_adapter import LocalStorageAdapter
from app.adapters.storage.policy import PayloadPolicyManager
from app.core.config import settings


@pytest.mark.asyncio
async def test_local_storage_basic_io(tmp_path):
    adapter = LocalStorageAdapter(base_dir=str(tmp_path))
    key = "test/sample.txt"
    content = b"Hello, ApexFlow Storage!"

    # Save
    saved_key = await adapter.save(key, content, content_type="text/plain")
    assert saved_key == key

    # Exists
    assert await adapter.exists(key) is True

    # Get
    retrieved = await adapter.get(key)
    assert retrieved == content

    # Delete
    deleted = await adapter.delete(key)
    assert deleted is True
    assert await adapter.exists(key) is False


@pytest.mark.asyncio
async def test_single_payload_size_limit(tmp_path):
    adapter = LocalStorageAdapter(base_dir=str(tmp_path))
    # Exceeding 2MB limit should raise ValueError
    large_content = b"x" * (settings.PAYLOAD_MAX_SINGLE_BYTES + 100)
    with pytest.raises(ValueError, match="exceeds maximum single payload limit"):
        await adapter.save("large_file.bin", large_content)


@pytest.mark.asyncio
async def test_path_traversal_prevention(tmp_path):
    adapter = LocalStorageAdapter(base_dir=str(tmp_path))
    with pytest.raises(ValueError, match="path traversal"):
        await adapter.save("../../../etc/passwd", b"malicious content")


@pytest.mark.asyncio
async def test_payload_policy_manager_offload(tmp_path):
    # Small payload <= 250KB inline threshold
    small_payload = {"data": "small payload"}
    assert PayloadPolicyManager.should_offload(small_payload) is False

    # Large payload > 250KB inline threshold
    large_payload = {"data": "A" * (settings.PAYLOAD_MAX_INLINE_BYTES + 100)}
    assert PayloadPolicyManager.should_offload(large_payload) is True

    # Process offload
    ref, is_offloaded = await PayloadPolicyManager.process_and_offload_if_needed(large_payload)
    assert is_offloaded is True
    assert PayloadPolicyManager.is_ref(ref) is True
    assert ref["$apexflow_ref"] is True
    assert ref["size_bytes"] > settings.PAYLOAD_MAX_INLINE_BYTES
