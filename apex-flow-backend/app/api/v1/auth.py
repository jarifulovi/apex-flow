import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_from_jwt, get_jwt_payload
from app.schemas.auth import UserProfile, SessionResponse

router = APIRouter(prefix="/auth")


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
    description=(
        "Returns the authenticated user's profile derived from the Supabase JWT claims. "
        "No database query is performed — user identity is sourced entirely from the token."
    ),
)
async def get_me(
    payload: Dict[str, Any] = Depends(get_jwt_payload),
) -> UserProfile:
    """
    Returns the current user's profile from JWT claims.

    Supabase embeds the following useful claims in the token:
    - sub: UUID of the user (auth.users.id)
    - email: user's email address
    - user_metadata.full_name: display name set during signup
    - user_metadata.avatar_url: avatar URL (if set)
    """
    user_metadata = payload.get("user_metadata") or {}

    return UserProfile(
        id=uuid.UUID(payload["sub"]),
        email=payload.get("email"),
        full_name=user_metadata.get("full_name"),
        avatar_url=user_metadata.get("avatar_url"),
    )


@router.get(
    "/session",
    response_model=SessionResponse,
    summary="Validate current session",
    description=(
        "Lightweight endpoint to verify that the Bearer JWT is valid and not expired. "
        "Returns the user_id on success. Use this as a session health check from the dashboard."
    ),
)
async def validate_session(
    user_id: uuid.UUID = Depends(get_current_user_from_jwt),
) -> SessionResponse:
    """Validates the JWT and returns a session validity response."""
    return SessionResponse(valid=True, user_id=user_id)
