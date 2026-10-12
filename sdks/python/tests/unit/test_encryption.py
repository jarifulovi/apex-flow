import pytest
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
from dataclasses import dataclass

from apex_flow_sdk.core.client import ApexFlowClient
from apex_flow_sdk.core.context import WorkflowContext
from apex_flow_sdk.core.encryption import (
    ENCRYPTED_KEY,
    EncryptedPayloadEnvelope,
    decrypt_payload,
    encrypt_payload,
    is_encrypted,
    normalize_key,
)


class SampleModel(BaseModel):
    user_id: uuid.UUID
    name: str
    amount: float
    created_at: datetime


@dataclass
class SampleDataClass:
    sku: str
    qty: int


def test_key_normalization():
    # Passphrase derived via SHA-256
    k1 = normalize_key("my-secret-passphrase")
    assert len(k1) == 32

    # Deterministic derivation
    k2 = normalize_key("my-secret-passphrase")
    assert k1 == k2

    # 64-char hex string
    hex_key = "a" * 64
    k3 = normalize_key(hex_key)
    assert len(k3) == 32
    assert k3 == bytes.fromhex(hex_key)

    # 32 raw bytes
    raw_32 = b"\x01" * 32
    k4 = normalize_key(raw_32)
    assert k4 == raw_32


def test_encryption_roundtrip_dict():
    key = "super-secret-key-12345"
    payload = {
        "account_id": "ACC-998811",
        "balance": 15000.75,
        "is_active": True,
        "tags": ["vip", "enterprise"],
        "metadata": {"region": "us-east", "tier": 1},
    }

    envelope = encrypt_payload(payload, key)
    assert is_encrypted(envelope) is True
    assert envelope[ENCRYPTED_KEY] is True
    assert envelope["alg"] == "AES-256-GCM"
    assert "iv" in envelope
    assert "ciphertext" in envelope
    assert "key_hint" in envelope

    # Plaintext fields must NOT be visible in envelope
    assert "account_id" not in envelope
    assert "balance" not in envelope

    # Decrypt
    decrypted = decrypt_payload(envelope, key)
    assert decrypted == payload


def test_encryption_roundtrip_pydantic_and_dataclass():
    key = "pydantic-secret-key"
    uid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    model = SampleModel(user_id=uid, name="Alice", amount=99.9, created_at=now)

    envelope = encrypt_payload(model, key)
    assert is_encrypted(envelope) is True

    decrypted = decrypt_payload(envelope, key)
    assert decrypted["user_id"] == str(uid)
    assert decrypted["name"] == "Alice"
    assert decrypted["amount"] == 99.9
    assert decrypted["created_at"].replace("Z", "+00:00") == now.isoformat()


def test_tampered_ciphertext_fails():
    key = "test-key"
    payload = {"data": "confidential"}
    envelope = encrypt_payload(payload, key)

    # Tamper with ciphertext
    import base64
    ct_bytes = bytearray(base64.b64decode(envelope["ciphertext"]))
    ct_bytes[0] ^= 0xFF  # Flip bits
    envelope["ciphertext"] = base64.b64encode(ct_bytes).decode("ascii")

    with pytest.raises(ValueError, match="Failed to decrypt payload"):
        decrypt_payload(envelope, key)


def test_wrong_key_fails():
    key1 = "key-alpha"
    key2 = "key-beta"
    payload = {"data": "classified"}
    envelope = encrypt_payload(payload, key1)

    with pytest.raises(ValueError, match="Failed to decrypt payload"):
        decrypt_payload(envelope, key2)


@pytest.mark.asyncio
async def test_workflow_context_encryption_and_checkpoint_recovery():
    key = "workflow-e2ee-key"
    client = ApexFlowClient(base_url="http://mock", encryption_key=key)

    reported_payloads = []

    # Mock HTTP client responses
    async def mock_post(url, **kwargs):
        class MockRes:
            status_code = 201
            def json(self):
                return {"id": "step-123"}
        if "/api/v1/steps/report" in url:
            reported_payloads.append(kwargs.get("json", {}))
        return MockRes()

    client.http_client.post = mock_post

    run_id = uuid.uuid4()
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)

    # Step returns confidential data
    async def process_pii():
        return {"ssn": "123-45-6789", "name": "Jane Doe"}

    result = await ctx.step("process_pii", process_pii)
    # Inside local worker process, step returned plaintext
    assert result == {"ssn": "123-45-6789", "name": "Jane Doe"}

    # What was reported over the wire to control plane must be encrypted!
    assert len(reported_payloads) == 1
    reported_output = reported_payloads[0]["output_payload"]
    assert is_encrypted(reported_output) is True
    assert reported_output[ENCRYPTED_KEY] is True
    assert "ssn" not in reported_output

    # Simulate worker crash & recovery:
    # A fresh worker restarts with the same encryption key and fetches checkpoints
    fresh_client = ApexFlowClient(base_url="http://mock", encryption_key=key)
    async def mock_get(url):
        class MockRes:
            status_code = 200
            def json(self):
                return {
                    "steps": [
                        {
                            "id": "step-123",
                            "step_name": "process_pii",
                            "step_order": 1,
                            "status": "success",
                            "output_payload": reported_output,  # Encrypted in DB!
                        }
                    ]
                }
        return MockRes()

    fresh_client.http_client.get = mock_get
    fresh_ctx = WorkflowContext(workflow_run_id=run_id, client=fresh_client)

    # Re-executing step skips computation and recovers decrypted checkpoint!
    step_executed = False
    async def should_not_run():
        nonlocal step_executed
        step_executed = True
        return {"unexpected": "data"}

    recovered_val = await fresh_ctx.step("process_pii", should_not_run)
    assert step_executed is False
    assert recovered_val == {"ssn": "123-45-6789", "name": "Jane Doe"}


def test_missing_key_on_encrypted_envelope_raises_error():
    from apex_flow_sdk.core.encryption import decrypt_if_encrypted
    envelope = encrypt_payload({"data": 123}, "secret")
    with pytest.raises(ValueError, match="no encryption_key was provided"):
        decrypt_if_encrypted(envelope, None)


def test_malformed_envelope_handling():
    with pytest.raises(ValueError, match="Malformed encrypted payload envelope"):
        decrypt_payload({"$apexflow_encrypted": True, "iv": "not-valid-base64!!!", "ciphertext": "abc"}, "secret")


def test_primitive_and_empty_payload_roundtrip():
    key = "primitives-key"
    for item in [{}, [], "", 0, 42.5, False, True, ["a", 1, {"nested": None}]]:
        envelope = encrypt_payload(item, key)
        assert is_encrypted(envelope) is True
        decrypted = decrypt_payload(envelope, key)
        assert decrypted == item

