from functools import lru_cache
import hashlib
import secrets
from typing import Any, Dict, Tuple
import jwt
from jwt import PyJWKClient, PyJWTError
from app.core.config import settings
from app.core.exceptions import UnauthorizedException


def generate_project_key(prefix: str = "af_live_") -> Tuple[str, str, str]:
    """
    Generates a secure random API key.
    Returns a tuple: (raw_key, key_prefix, key_hash)
    - raw_key is shown ONCE to the user upon creation.
    - key_prefix is stored to identify the key in UI.
    - key_hash (SHA-256) is stored in the database.
    """
    secret = secrets.token_urlsafe(24)
    raw_key = f"{prefix}{secret}"
    key_prefix = f"{prefix}{secret[:4]}"
    key_hash = hash_api_key(raw_key)
    return raw_key, key_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    """Computes SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


@lru_cache(maxsize=4)
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    """Cached PyJWKClient instance for fetching Supabase public keys."""
    return PyJWKClient(jwks_url, cache_keys=True)


def decode_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Decodes and cryptographically verifies a Supabase JWT token.
    Extracts claims including 'sub' (the user_id UUID).
    Strictly fails if verification fails. Absolutely no unverified fallback.
    """
    if not token or not token.strip():
        raise UnauthorizedException("Missing or empty JWT token.")

    token = token.strip()

    try:
        header = jwt.get_unverified_header(token)
    except PyJWTError as err:
        raise UnauthorizedException(f"Invalid JWT header format: {err}")

    alg = header.get("alg", "HS256")
    jwks_url = (getattr(settings, "SUPABASE_JWKS_URL", None) or "").strip()
    secret = (getattr(settings, "SUPABASE_JWT_SECRET", None) or "").strip()
    placeholder_secrets = {"your-supabase-jwt-secret-here", "change-me", ""}

    # 1. Resolve cryptographic verification key
    if alg in ("RS256", "ES256"):
        if not jwks_url:
            raise UnauthorizedException("JWT verification failed: SUPABASE_JWKS_URL is not configured.")
        try:
            client = _get_jwks_client(jwks_url)
            key = client.get_signing_key_from_jwt(token).key
        except Exception as err:
            raise UnauthorizedException(f"Failed to retrieve JWKS signing key: {err}")

    elif alg == "HS256":
        if not secret or secret in placeholder_secrets:
            raise UnauthorizedException("JWT verification failed: SUPABASE_JWT_SECRET is not configured.")
        key = secret

    else:
        raise UnauthorizedException(f"Unsupported JWT signing algorithm: {alg}")

    # 2. Single unified cryptographic verification
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[alg],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Supabase JWT token has expired.")
    except PyJWTError as err:
        raise UnauthorizedException(f"Invalid Supabase JWT signature: {err}")

    # 3. Validate standard user identity claim
    if "sub" not in payload or not payload["sub"]:
        raise UnauthorizedException("Invalid Supabase JWT token: missing 'sub' claim.")

    return payload



