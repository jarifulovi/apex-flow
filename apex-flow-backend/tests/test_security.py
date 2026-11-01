import time
import uuid
import jwt
import pytest
from unittest.mock import patch

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_supabase_jwt, generate_project_key, hash_api_key


def test_generate_and_hash_project_key():
    """Verify generated API keys follow format and hash correctly"""
    raw_key, prefix, key_hash = generate_project_key()
    assert raw_key.startswith("af_live_")
    assert prefix.startswith("af_live_")
    assert len(prefix) == len("af_live_") + 4
    assert hash_api_key(raw_key) == key_hash


def test_decode_valid_hs256_jwt():
    """Verify valid HS256 token signed with configured secret decodes correctly"""
    user_id = str(uuid.uuid4())
    secret = settings.SUPABASE_JWT_SECRET
    token = jwt.encode(
        {"sub": user_id, "exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256",
    )

    payload = decode_supabase_jwt(token)
    assert payload["sub"] == user_id


def test_decode_expired_jwt_fails():
    """Verify expired token raises UnauthorizedException without fallback"""
    user_id = str(uuid.uuid4())
    secret = settings.SUPABASE_JWT_SECRET
    expired_token = jwt.encode(
        {"sub": user_id, "exp": int(time.time()) - 100},
        secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedException, match="expired"):
        decode_supabase_jwt(expired_token)


def test_decode_tampered_signature_fails():
    """Verify forged signature is rejected immediately without unverified fallback"""
    user_id = str(uuid.uuid4())
    forged_token = jwt.encode(
        {"sub": user_id, "exp": int(time.time()) + 3600},
        "attacker-fake-secret-key-that-does-not-match",
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedException, match="Invalid Supabase JWT signature"):
        decode_supabase_jwt(forged_token)


def test_decode_missing_sub_claim_fails():
    """Verify token lacking 'sub' user identity claim is rejected"""
    secret = settings.SUPABASE_JWT_SECRET
    token_without_sub = jwt.encode(
        {"email": "user@example.com", "exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedException, match="missing 'sub' claim"):
        decode_supabase_jwt(token_without_sub)


def test_decode_empty_token_fails():
    """Verify empty or whitespace token raises UnauthorizedException"""
    with pytest.raises(UnauthorizedException, match="Missing or empty JWT token"):
        decode_supabase_jwt("")
    with pytest.raises(UnauthorizedException, match="Missing or empty JWT token"):
        decode_supabase_jwt("   ")


def test_decode_unsupported_alg_fails():
    """Verify unsupported algorithm (e.g., 'none') is strictly rejected"""
    # Create an unsigned 'none' algorithm token
    token = jwt.encode({"sub": str(uuid.uuid4())}, key="", algorithm="none")
    with pytest.raises(UnauthorizedException, match="Unsupported JWT signing algorithm"):
        decode_supabase_jwt(token)


def test_decode_missing_secret_fails_honestly():
    """Verify if secret is missing or placeholder, it fails with clear message"""
    user_id = str(uuid.uuid4())
    token = jwt.encode({"sub": user_id}, "some-secret", algorithm="HS256")
    with patch.object(settings, "SUPABASE_JWT_SECRET", None):
        with pytest.raises(UnauthorizedException, match="SUPABASE_JWT_SECRET is not configured"):
            decode_supabase_jwt(token)
