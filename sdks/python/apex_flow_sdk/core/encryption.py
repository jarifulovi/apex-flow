"""
ApexFlow Zero-Knowledge Payload Encryption Engine
==================================================
Provides client-side AES-256-GCM authenticated encryption and decryption
for workflow step inputs and outputs. Ensures that payloads stored in
PostgreSQL and Cloudflare R2 / S3 remain encrypted ciphertext, decryptable
only by authorized workers and browsers possessing the encryption key.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any, Dict, Optional, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import BaseModel, Field

from apex_flow_sdk.core.serialization import json_dumps

ENCRYPTED_KEY = "$apexflow_encrypted"


class EncryptedPayloadEnvelope(BaseModel):
    """
    Standard JSONB envelope representing an AES-256-GCM encrypted payload.
    Compatible with browser Web Crypto API (SubtleCrypto).
    """

    is_encrypted: bool = Field(True, alias="$apexflow_encrypted")
    alg: str = "AES-256-GCM"
    iv: str = Field(..., description="Base64 encoded 12-byte initialization vector")
    ciphertext: str = Field(
        ...,
        description="Base64 encoded ciphertext including 16-byte authentication tag",
    )
    key_hint: Optional[str] = Field(
        None, description="First 6 hex characters of key fingerprint for UI hints"
    )

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


def normalize_key(key: Union[str, bytes]) -> bytes:
    """
    Normalizes an encryption key into a 32-byte AES-256 key.
    Supports:
      1. 64-character hex strings (32 raw bytes)
      2. 44-character base64 strings (32 raw bytes)
      3. Arbitrary passphrase strings (derived via SHA-256)
      4. 32-byte raw bytes
    """
    if isinstance(key, str):
        key_str = key.strip()
        # 1. 64-char hex key
        if len(key_str) == 64:
            try:
                return bytes.fromhex(key_str)
            except ValueError:
                pass
        # 2. 44-char base64 key
        if len(key_str) == 44:
            try:
                decoded = base64.b64decode(key_str)
                if len(decoded) == 32:
                    return decoded
            except Exception:
                pass
        # 3. Arbitrary passphrase derived with SHA-256
        return hashlib.sha256(key_str.encode("utf-8")).digest()

    elif isinstance(key, bytes):
        if len(key) == 32:
            return key
        return hashlib.sha256(key).digest()

    raise ValueError("Encryption key must be a non-empty string or bytes.")


def get_key_hint(key_bytes: bytes) -> str:
    """Returns a 6-character hex fingerprint of the key to aid multi-key debugging."""
    return hashlib.sha256(key_bytes).hexdigest()[:6]


def is_encrypted(obj: Any) -> bool:
    """Check if a Python object is an ApexFlow encrypted payload envelope."""
    return isinstance(obj, dict) and obj.get(ENCRYPTED_KEY) is True


def encrypt_payload(payload: Any, key: Union[str, bytes]) -> Dict[str, Any]:
    """
    Encrypts an arbitrary Python object or JSON structure into an AES-256-GCM envelope.
    """
    if is_encrypted(payload):
        return payload

    key_bytes = normalize_key(key)
    raw_json = json_dumps(payload)
    data_bytes = raw_json.encode("utf-8")

    # Standard 12-byte random IV for AES-GCM
    iv = os.urandom(12)
    aesgcm = AESGCM(key_bytes)
    # AESGCM.encrypt appends the 16-byte tag to the ciphertext
    ciphertext_with_tag = aesgcm.encrypt(iv, data_bytes, None)

    envelope = EncryptedPayloadEnvelope(
        is_encrypted=True,
        alg="AES-256-GCM",
        iv=base64.b64encode(iv).decode("ascii"),
        ciphertext=base64.b64encode(ciphertext_with_tag).decode("ascii"),
        key_hint=get_key_hint(key_bytes),
    )
    return envelope.model_dump(by_alias=True)


def decrypt_payload(envelope: Dict[str, Any], key: Union[str, bytes]) -> Any:
    """
    Decrypts an AES-256-GCM envelope back into its native Python object.
    Raises ValueError on invalid keys or corrupted tags.
    """
    if not is_encrypted(envelope):
        return envelope

    key_bytes = normalize_key(key)
    try:
        iv = base64.b64decode(envelope["iv"])
        ciphertext_with_tag = base64.b64decode(envelope["ciphertext"])
    except Exception as e:
        raise ValueError(f"Malformed encrypted payload envelope: {e}") from e

    aesgcm = AESGCM(key_bytes)
    try:
        decrypted_bytes = aesgcm.decrypt(iv, ciphertext_with_tag, None)
    except Exception as e:
        hint = envelope.get("key_hint")
        hint_msg = f" (expected key fingerprint: {hint})" if hint else ""
        raise ValueError(
            f"Failed to decrypt payload. The provided encryption key is incorrect or data was tampered with{hint_msg}."
        ) from e

    decrypted_str = decrypted_bytes.decode("utf-8")
    return json.loads(decrypted_str)


def encrypt_if_key_provided(payload: Any, key: Optional[Union[str, bytes]]) -> Any:
    """Encrypt payload if key is supplied and payload is not already encrypted."""
    if key is not None and not is_encrypted(payload):
        return encrypt_payload(payload, key)
    return payload


def decrypt_if_encrypted(payload: Any, key: Optional[Union[str, bytes]]) -> Any:
    """Decrypt payload if it is an encrypted envelope. Raises error if key is missing."""
    if is_encrypted(payload):
        if not key:
            raise ValueError(
                "Payload is end-to-end encrypted ($apexflow_encrypted=true), but no encryption_key "
                "was provided to ApexFlowClient. Set APEXFLOW_ENCRYPTION_KEY to decrypt."
            )
        return decrypt_payload(payload, key)
    return payload
