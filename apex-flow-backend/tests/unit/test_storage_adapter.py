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


def test_storage_policy_local_in_dev(monkeypatch, tmp_path):
    from app.adapters.storage.policy import get_storage_adapter, reset_storage_adapter
    reset_storage_adapter()

    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "STORAGE_LOCAL_DIR", str(tmp_path))

    adapter = get_storage_adapter()
    assert isinstance(adapter, LocalStorageAdapter)
    reset_storage_adapter()


def test_storage_policy_local_forbidden_in_production(monkeypatch):
    from app.adapters.storage.policy import get_storage_adapter, reset_storage_adapter
    reset_storage_adapter()

    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    with pytest.raises(RuntimeError, match="STORAGE_PROVIDER='local' is forbidden in production"):
        get_storage_adapter()
    reset_storage_adapter()


def test_storage_policy_s3_missing_bucket_fails_fast_without_fallback(monkeypatch):
    from app.adapters.storage.policy import get_storage_adapter, reset_storage_adapter
    reset_storage_adapter()

    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", None)

    # Must raise RuntimeError immediately and NOT silently fall back to local disk
    with pytest.raises(RuntimeError, match="S3_BUCKET_NAME is not configured"):
        get_storage_adapter()
    reset_storage_adapter()


def test_storage_policy_s3_valid_configuration(monkeypatch):
    from app.adapters.storage.policy import get_storage_adapter, reset_storage_adapter
    from app.adapters.storage.s3_adapter import S3StorageAdapter
    reset_storage_adapter()

    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "my-test-bucket")
    monkeypatch.setattr(settings, "AWS_ACCESS_KEY_ID", "mock-access-key")
    monkeypatch.setattr(settings, "AWS_SECRET_ACCESS_KEY", "mock-secret-key")
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "https://mock.r2.cloudflarestorage.com")

    adapter = get_storage_adapter()
    assert isinstance(adapter, S3StorageAdapter)
    assert adapter.bucket_name == "my-test-bucket"
    reset_storage_adapter()


def test_storage_policy_cloudflare_alias(monkeypatch):
    from app.adapters.storage.policy import get_storage_adapter, reset_storage_adapter
    from app.adapters.storage.s3_adapter import S3StorageAdapter
    reset_storage_adapter()

    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "cloudflare")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "r2-bucket")
    monkeypatch.setattr(settings, "AWS_ACCESS_KEY_ID", "r2-key")
    monkeypatch.setattr(settings, "AWS_SECRET_ACCESS_KEY", "r2-secret")

    adapter = get_storage_adapter()
    assert isinstance(adapter, S3StorageAdapter)
    assert adapter.bucket_name == "r2-bucket"
    reset_storage_adapter()


def test_storage_policy_invalid_provider_raises_value_error(monkeypatch):
    from app.adapters.storage.policy import get_storage_adapter, reset_storage_adapter
    reset_storage_adapter()

    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "ftp_server")

    with pytest.raises(ValueError, match="Invalid STORAGE_PROVIDER"):
        get_storage_adapter()
    reset_storage_adapter()


@pytest.mark.asyncio
async def test_s3_adapter_size_limit():
    from app.adapters.storage.s3_adapter import S3StorageAdapter
    adapter = S3StorageAdapter(
        bucket_name="test-bucket",
        aws_access_key_id="mock-key",
        aws_secret_access_key="mock-secret",
    )
    oversized_content = b"x" * (settings.PAYLOAD_MAX_SINGLE_BYTES + 10)
    with pytest.raises(ValueError, match="exceeds maximum single payload limit"):
        await adapter.save("too_big.bin", oversized_content)
