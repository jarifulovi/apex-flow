import hashlib
import secrets
from typing import Any, Dict, Tuple
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


def decode_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies a Supabase JWT token.
    Extracts claims including 'sub' (the user_id UUID).
    """
    try:
        # If SUPABASE_JWT_SECRET is configured, verify signature
        secret = getattr(settings, "SUPABASE_JWT_SECRET", None)
        if secret:
            payload = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
        else:
            # Unverified decode for development/testing when secret is not set
            payload = jwt.decode(token, options={"verify_signature": False})

        if "sub" not in payload:
            raise UnauthorizedException("Invalid Supabase JWT token: missing user ID claim.")

        return payload
    except jwt.PyJWTError as e:
        raise UnauthorizedException(f"Invalid or expired Supabase JWT token: {str(e)}")
