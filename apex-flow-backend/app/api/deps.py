import uuid
from typing import Any, Dict, Optional
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import UnauthorizedException, decode_supabase_jwt
from app.schemas.project import ProjectKeyContext
from app.services.project_key_service import ProjectKeyService


async def get_current_project_key_context(
    x_apexflow_project_key: Optional[str] = Header(None, alias="X-ApexFlow-Project-Key"),
    db: AsyncSession = Depends(get_db),
) -> ProjectKeyContext:
    """
    Dependency for SDK/Worker endpoints requiring full API Key context.
    Authenticates requests via the X-ApexFlow-Project-Key header.
    Returns ProjectKeyContext (project_id, owner_id, key_id).
    """
    if not x_apexflow_project_key:
        raise UnauthorizedException("Missing X-ApexFlow-Project-Key header.")

    return await ProjectKeyService.authenticate_api_key(
        db=db, raw_key=x_apexflow_project_key
    )


async def get_current_user_from_api_key(
    x_apexflow_project_key: Optional[str] = Header(None, alias="X-ApexFlow-Project-Key"),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """
    Dependency returning owner_id from X-ApexFlow-Project-Key.
    """
    ctx = await get_current_project_key_context(
        x_apexflow_project_key=x_apexflow_project_key, db=db
    )
    return ctx.owner_id


def _extract_user_id(payload: Dict[str, Any]) -> uuid.UUID:
    """Parse the 'sub' claim from a decoded JWT payload into a UUID."""
    user_id_str = payload.get("sub")
    try:
        return uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise UnauthorizedException("Invalid user ID in JWT sub claim.")


def _decode_bearer(authorization: Optional[str]) -> Dict[str, Any]:
    """Extract and decode the Bearer token from an Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException("Missing or invalid Authorization header.")
    token = authorization.split("Bearer ", 1)[1].strip()
    return decode_supabase_jwt(token)


async def get_current_user_from_jwt(
    authorization: Optional[str] = Header(None),
) -> uuid.UUID:
    """
    Dependency for Dashboard UI endpoints.
    Authenticates requests via the Bearer Supabase JWT in Authorization header.
    Returns user_id / owner_id (sub claim).
    """
    payload = _decode_bearer(authorization)
    return _extract_user_id(payload)


async def get_current_user_from_any_auth(
    authorization: Optional[str] = Header(None),
    x_apexflow_project_key: Optional[str] = Header(None, alias="X-ApexFlow-Project-Key"),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """
    Authenticates requests via either Bearer JWT (for Dashboard UI)
    or X-ApexFlow-Project-Key header (for SDK/Workers).
    Returns owner_id.
    """
    if authorization and authorization.startswith("Bearer "):
        payload = _decode_bearer(authorization)
        return _extract_user_id(payload)
    elif x_apexflow_project_key:
        ctx = await get_current_project_key_context(
            x_apexflow_project_key=x_apexflow_project_key, db=db
        )
        return ctx.owner_id
    else:
        raise UnauthorizedException("Authentication required via Bearer token or Project Key.")


async def get_jwt_payload(
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Dependency that returns the full decoded JWT payload."""
    return _decode_bearer(authorization)
