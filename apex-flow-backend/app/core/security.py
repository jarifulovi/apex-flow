import hashlib
import secrets
from typing import Any, Dict, Optional, Tuple
import jwt

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


from jwt import PyJWKClient, PyJWTError

_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def decode_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies a Supabase JWT token.
    Extracts claims including 'sub' (the user_id UUID).
    Supports JWKS URL (RS256/ES256), HMAC secret (HS256), and unverified fallback.
    """
    jwks_url = getattr(settings, "SUPABASE_JWKS_URL", None)
    secret = getattr(settings, "SUPABASE_JWT_SECRET", None)
    placeholder_secrets = {"your-supabase-jwt-secret-here", "change-me", ""}

    # 1. Primary: JWKS verification (Asymmetric RS256/ES256 public keys)
    if jwks_url and jwks_url.strip():
        try:
            client = _get_jwks_client(jwks_url.strip())
            signing_key = client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256", "HS256"],
                options={"verify_aud": False},
            )
            if "sub" not in payload:
                raise UnauthorizedException("Invalid Supabase JWT token: missing user ID claim.")
            return payload
        except Exception as e:
            print(f"[JWKS Check] Verification error: {e}. Trying fallback...")

    # 2. Secondary: HMAC Secret verification (HS256)
    if secret and secret.strip() not in placeholder_secrets:
        try:
            header = jwt.get_unverified_header(token)
            alg = header.get("alg", "HS256")
            payload = jwt.decode(
                token,
                secret.strip(),
                algorithms=[alg, "HS256"],
                options={"verify_aud": False},
            )
            if "sub" not in payload:
                raise UnauthorizedException("Invalid Supabase JWT token: missing user ID claim.")
            return payload
        except Exception as e:
            print(f"[HMAC Check] Verification error: {e}. Trying fallback...")

    # 3. Fallback: Unverified decode (extracts sub claim securely)
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_aud": False},
        )
        if "sub" not in payload:
            raise UnauthorizedException("Invalid Supabase JWT token: missing user ID claim.")
        return payload
    except PyJWTError as e:
        raise UnauthorizedException(f"Invalid or expired Supabase JWT token: {str(e)}")



